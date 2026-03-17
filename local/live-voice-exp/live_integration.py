import asyncio
from google import genai
from google.genai import types
import pyaudio
import cv2
import mss
import numpy as np
from dotenv import load_dotenv
from typing import Literal

import platform
import ctypes

# Force Windows to ignore display scaling for this Python process
if platform.system() == "Windows":
    try:
        # Windows 8.1 and later: Per-monitor DPI awareness
        ctypes.windll.shcore.SetProcessDpiAwareness(2) 
    except Exception:
        try:
            # Fallback for older Windows versions
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            print(f"[SYSTEM] Could not set DPI awareness: {e}")

load_dotenv()

# --- Custom Screenshot Functions ---
def capture_screen(monitor_index: int = 1) -> np.ndarray:
    """Captures the screen and returns it as a BGR NumPy array."""
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        sct_img = sct.grab(monitor)
        img_bgr = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
        return img_bgr

# --- Custom Action Functions ---
# Make sure your take_action function is accessible here. 
# You can paste it above, or import it if it is in another file:
from action import take_action 

def execute_pc_action(action: Literal['click', 'double_click', 'right_click', 'click_and_type', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'], target: str = "", value: str = "") -> dict:
    """Executes a PC automation action on the user's screen.
    
    Args:
        action: The type of action to perform. Must be strictly one of: 'click', 'double_click', 'right_click', 'click_and_type', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'.
        target: The normalized y, x coordinates (e.g., '500, 500') scaled between 0 and 1000. Required for click/type actions.
        value: The text to type, keyboard key (e.g., 'enter', 'win'), hotkeys (e.g., 'ctrl, c'), scroll amount, or wait seconds. Required for non-click actions.
    """
    actions_dict = {'action': action}
    if target: 
        actions_dict['target'] = target
    if value: 
        actions_dict['value'] = value

    print(f"\n[SYSTEM] Executing local action: {actions_dict}")
    try:
        take_action(actions_dict)
        return {"status": "success", "message": f"Successfully performed {action}."}
    except Exception as e:
        return {"status": "error", "message": f"Failed due to error: {str(e)}"}

def request_screenshot():
    """Takes a screenshot of the user's current screen and uploads it to your visual context so you can see the UI."""
    pass


# --- API Setup ---
client = genai.Client()

# --- pyaudio config ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

pya = pyaudio.PyAudio()

AGENT_PROMPT = """You are an advanced, autonomous hands-free PC assistant running on the user's local machine. You navigate the UI visually and interact using exact commands.

YOUR CAPABILITIES (via execute_pc_action):
1. `click`: Single left click (requires target [y, x])
2. `double_click`: Double click, useful for desktop icons (requires target [y, x])
3. `right_click`: Open context menus (requires target [y, x])
4. `click_and_type`: Click a field and type full text (requires target [y, x] and value)
5. `type_text`: Type full continuous text directly without clicking (requires value)
6. `press_key`: Press a single key like 'enter', 'win', 'esc', 'tab', 'backspace' (requires value)
7. `hotkey`: Press multiple keys like 'win, r' or 'ctrl, c' (requires value, comma-separated)
8. `scroll`: Scroll the page (requires value: positive int for up, negative for down)
9. `wait`: Pause execution for UI loading (requires value: seconds as float)

YOUR WORKFLOW (STRICT):
1. OBSERVE: Whenever the user gives a command, ask for a screenshot to see the screen's state.
2. REASON: Look at the visual context. What do you need to do next? 
3. ACT: Call `execute_pc_action`. Target coordinates MUST be normalized [y, x] mapped to a 1000x1000 grid.
4. VERIFY: Call `request_screenshot` to verify state changes, BUT CRITICALLY: DO NOT request screenshots between single letters or rapid keypresses! Batch your typing into full words or sentences via `type_text` or `click_and_type`, and ONLY request a new screenshot after a major structural UI change (like opening an app, submitting a form, or clicking a button).

WINDOWS CHEAT CODES:
- The fastest way to open an app is not to click its icon. Use `execute_pc_action` with `press_key` and value `win`, then type the app name, then `press_key` with value `enter`.
- If a UI element needs time to load, use the `wait` action for 1-2 seconds before requesting your next screenshot.
- If you made a mistake (e.g. invalid key), read the error message you receive back, self-correct, and try again.
"""

# --- Live API config ---
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
CONFIG = {
    "response_modalities": ["AUDIO"],
    "system_instruction": AGENT_PROMPT,
    "tools": [execute_pc_action, request_screenshot]
}

audio_queue_output = asyncio.Queue()
audio_queue_mic = asyncio.Queue(maxsize=5)
audio_stream = None

async def listen_audio():
    """Listens for audio and puts it into the mic audio queue."""
    global audio_stream
    mic_info = pya.get_default_input_device_info()
    audio_stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        input_device_index=mic_info["index"],
        frames_per_buffer=CHUNK_SIZE,
    )
    kwargs = {"exception_on_overflow": False} if __debug__ else {}
    while True:
        data = await asyncio.to_thread(audio_stream.read, CHUNK_SIZE, **kwargs)
        await audio_queue_mic.put({"data": data, "mime_type": "audio/pcm"})

async def send_realtime(session):
    """Sends audio from the mic audio queue to the GenAI session."""
    while True:
        msg = await audio_queue_mic.get()
        await session.send_realtime_input(audio=msg)

async def receive_from_gemini(session):
    """Receives responses from GenAI, handles audio, and executes tool calls."""
    while True:
        turn = session.receive()
        async for response in turn:
            
            # 1. Handle incoming Audio (Speak back to the user)
            if response.server_content and response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if part.inline_data and isinstance(part.inline_data.data, bytes):
                        audio_queue_output.put_nowait(part.inline_data.data)

            # 2. Handle incoming Tool Calls (Execute PC actions & Screenshots)
            if response.tool_call:
                for function_call in response.tool_call.function_calls:
                    name = function_call.name
                    args = function_call.args 
                    
                    if name == "execute_pc_action":
                        action_type = args.get("action")
                        target_label = args.get("target", "")
                        text_value = args.get("value", "")
                        
                        result_dict = execute_pc_action(action=action_type, target=target_label, value=text_value)
                        
                        await session.send_tool_response(
                            function_responses=[
                                types.FunctionResponse(
                                    id=function_call.id,
                                    name=name,
                                    response=result_dict
                                )
                            ]
                        )
                        
                    elif name == "request_screenshot":
                        print("\n[SYSTEM] Gemini requested a screenshot. Capturing...")
                        raw_img = await asyncio.to_thread(capture_screen)
                        success, buffer = cv2.imencode('.jpg', raw_img)
                        
                        if success:
                            # 1. Inject the image into the continuous stream
                            await session.send_realtime_input(
                                video=types.Blob(
                                    data=buffer.tobytes(), 
                                    mime_type="image/jpeg"
                                )
                            )
                            
                            # 2. Force the model to yield its locked turn
                            result_dict = {
                                "status": "success", 
                                "message": "Screenshot uploaded. SYSTEM RULE: You cannot see the image in this current turn. You must silently output nothing and end your turn. The system will auto-prompt you in 1 second."
                            }
                        else:
                            result_dict = {"status": "error", "message": "Failed to encode screenshot locally."}

                        # 3. Send the text-based tool response to close the paused turn
                        await session.send_tool_response(
                            function_responses=[
                                types.FunctionResponse(
                                    id=function_call.id,
                                    name=name,
                                    response=result_dict
                                )
                            ]
                        )
                        
                        # 4. THE FIX: Programmatically trigger a NEW turn so the context refreshes
                        if success:
                            print("[SYSTEM] Forcing context refresh for the new image...")
                            await asyncio.sleep(1.5) # Give the vision encoder time to digest the frame
                            
                            # Send a hidden text prompt to kickstart the AI again with the new visual context
                            await session.send_realtime_input(
                                text="System: The new screenshot is now in your visual context. Please analyze the grid and decide your next action or answer the user."
                            )

        # Empty the queue on interruption to stop playback
        while not audio_queue_output.empty():
            audio_queue_output.get_nowait()

async def play_audio():
    """Plays audio from the speaker audio queue."""
    stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=RECEIVE_SAMPLE_RATE,
        output=True,
    )
    while True:
        bytestream = await audio_queue_output.get()
        await asyncio.to_thread(stream.write, bytestream)

async def run():
    """Main function to run the audio loop."""
    try:
        async with client.aio.live.connect(
            model=MODEL, config=CONFIG
        ) as live_session:
            print("Connected to Gemini. Start speaking!")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_realtime(live_session))
                tg.create_task(listen_audio())
                tg.create_task(receive_from_gemini(live_session))
                tg.create_task(play_audio())
    except asyncio.CancelledError:
        pass
    finally:
        if audio_stream:
            audio_stream.close()
        pya.terminate()
        print("\nConnection closed.")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Interrupted by user.")