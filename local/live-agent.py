import asyncio
from google import genai
from google.genai import types
import pyaudio
from dotenv import load_dotenv
load_dotenv()

from action import execute_pc_action

client = genai.Client(
    
)

# --- pyaudio config ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

pya = pyaudio.PyAudio()

# --- Live API config ---
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
CONFIG = {
    "response_modalities": ["AUDIO"],
    "system_instruction": "You are a helpful hands-free PC assistant. When the user asks you to interact with the screen or keyboard, use the execute_pc_action tool to carry out their request.",
    "tools": [execute_pc_action] # The SDK will automatically parse your function, type hints, and docstring
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

# async def receive_audio(session):
#     """Receives responses from GenAI and puts audio data into the speaker audio queue."""
#     while True:
#         turn = session.receive()
#         async for response in turn:
#             if (response.server_content and response.server_content.model_turn):
#                 for part in response.server_content.model_turn.parts:
#                     if part.inline_data and isinstance(part.inline_data.data, bytes):
#                         audio_queue_output.put_nowait(part.inline_data.data)

#         # Empty the queue on interruption to stop playback
#         while not audio_queue_output.empty():
#             audio_queue_output.get_nowait()

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

            # 2. Handle incoming Tool Calls (Execute PC actions)
            if response.tool_call:
                for function_call in response.tool_call.function_calls:
                    name = function_call.name
                    args = function_call.args # These are the arguments Gemini decided to pass
                    
                    if name == "execute_pc_action":
                        # Extract arguments safely
                        action_type = args.get("action")
                        target_label = args.get("target", "")
                        text_value = args.get("value", "")
                        
                        # Run your local wrapper function
                        result_dict = execute_pc_action(action=action_type, target=target_label, value=text_value)
                        
                    # Send the confirmation back to the Gemini session
                        await session.send_tool_response(
                            function_responses=[
                                types.FunctionResponse(
                                    id=function_call.id,
                                    name=name,
                                    response=result_dict
                                )
                            ]
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