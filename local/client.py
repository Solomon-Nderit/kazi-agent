import asyncio
import websockets
import json
import base64
import keyboard
from audio_handler import AudioHandler, CHUNK_SIZE
from vision import capture_screen_as_base64
from action import take_action

import platform
import ctypes
from typing import Literal

if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) 
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def execute_pc_action(action: str, target: str = "", value: str = "") -> dict:
    actions_dict = {'action': action}
    if target: actions_dict['target'] = target
    if value: actions_dict['value'] = value

    print(f"\n[SYSTEM] Executing local action: {actions_dict}")
    try:
        take_action(actions_dict)
        return {"status": "success", "message": f"Successfully performed {action}."}
    except Exception as e:
        return {"status": "error", "message": f"Failed due to error: {str(e)}"}


async def client_loop():
    uri = "wss://kazi-copilot-brain-603050312015.us-central1.run.app"
    
    audio = AudioHandler()
    audio.start_playback()
    mic_stream = audio.start_recording()

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to cloud server...")
            
            async def send_audio():
                while True:
                    data = await asyncio.to_thread(mic_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                    await websocket.send(data)

            async def send_text_cli():
                while True:
                    # Wait for hotkey Ctrl+Alt+A
                    await asyncio.sleep(0.1)
                    if keyboard.is_pressed('ctrl+alt+a'):
                        # To avoid rapid re-triggering, sleep for a fraction
                        await asyncio.sleep(0.5)
                        text = await asyncio.to_thread(input, "\n[Prompt] Enter message: ")
                        if text.strip():
                            await websocket.send(json.dumps({
                                "type": "text",
                                "text": text
                            }))
                            print("[Prompt] Sent text to Gemini.")

            async def receive_messages():
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Playback audio
                        await asyncio.to_thread(audio.play_chunk, message)
                    else:
                        data = json.loads(message)
                        if data.get("type") == "tool_call":
                            name = data["name"]
                            args = data["args"]
                            call_id = data["id"]
                            
                            if name == "execute_pc_action":
                                result = execute_pc_action(**args)
                                await websocket.send(json.dumps({
                                    "type": "tool_response",
                                    "id": call_id,
                                    "name": name,
                                    "response": result
                                }))
                            
                            elif name == "request_screenshot":
                                print("Taking screenshot...")
                                b64_img = await asyncio.to_thread(capture_screen_as_base64)
                                
                                # Send image payload first
                                await websocket.send(json.dumps({
                                    "type": "image",
                                    "data": b64_img
                                }))
                                
                                # Then send tool response to close turn
                                await websocket.send(json.dumps({
                                    "type": "tool_response",
                                    "id": call_id,
                                    "name": name,
                                    "response": {
                                        "status": "success", 
                                        "message": "Screenshot uploaded. SYSTEM RULE: You cannot see the image in this current turn. You must silently output nothing and end your turn. The system will auto-prompt you in 1 second."
                                    },
                                    "is_screenshot": True
                                }))

            await asyncio.gather(send_audio(), send_text_cli(), receive_messages())

    except Exception as e:
        print(f"Disconnected: {e}")
    finally:
        audio.close()

if __name__ == "__main__":
    asyncio.run(client_loop())