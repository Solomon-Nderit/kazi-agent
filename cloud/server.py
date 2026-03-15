import asyncio
import json
import websockets
from google import genai
from google.genai import types
from tools import TOOLS

import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

with open("agent_prompt.md", "r") as f:
    AGENT_PROMPT = f.read()

CONFIG = {
    "response_modalities": ["AUDIO"],
    "system_instruction": AGENT_PROMPT,
    "tools": TOOLS
}

async def handle_client(websocket):
    print("Client connected!")
    try:
        async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
            
            async def receive_from_client():
                try:
                    async for message in websocket:
                        if isinstance(message, bytes):
                            # Audio from client -> gemini
                            await session.send_realtime_input(audio=types.Blob(data=message, mime_type="audio/pcm"))
                        else:
                            # JSON from client (tool responses or other images)
                            data = json.loads(message)
                            if "type" in data and data["type"] == "text":
                                await session.send_realtime_input(text=data["text"])
                            elif "type" in data and data["type"] == "tool_response":
                                resp = types.FunctionResponse(
                                    id=data["id"],
                                    name=data["name"],
                                    response=data["response"]
                                )
                                await session.send_tool_response(function_responses=[resp])
                                
                                # If it was a screenshot, client will also send an image payload soon
                                if data.get("is_screenshot"):
                                    await asyncio.sleep(1.5)
                                    await session.send_realtime_input(
                                        text="System: The new screenshot is now in your visual context. Please analyze the grid and decide your next action or answer the user."
                                    )
                            elif "type" in data and data["type"] == "image":
                                # Received image payload
                                import base64
                                img_bytes = base64.b64decode(data["data"])
                                await session.send_realtime_input(
                                    video=types.Blob(data=img_bytes, mime_type="image/jpeg")
                                )
                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception as e:
                    print(f"Client receive error: {e}")

            async def receive_from_gemini():
                try:
                    while True:
                        turn = session.receive()
                        async for response in turn:
                            # Handle Audio Output
                            if response.server_content and response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.inline_data and isinstance(part.inline_data.data, bytes):
                                        await websocket.send(part.inline_data.data)

                            # Handle Tool Calls
                            if response.tool_call:
                                for function_call in response.tool_call.function_calls:
                                    await websocket.send(json.dumps({
                                        "type": "tool_call",
                                        "id": function_call.id,
                                        "name": function_call.name,
                                        "args": function_call.args
                                    }))
                except Exception as e:
                    print(f"Gemini receive error: {e}")
            
            async with asyncio.TaskGroup() as tg:
                tg.create_task(receive_from_client())
                tg.create_task(receive_from_gemini())

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Cloud Run injects the PORT environment variable.
    # We fallback to 8765 for local testing if the var is missing.
    port = int(os.environ.get("PORT", 8765))
    
    async with websockets.serve(handle_client, "0.0.0.0", port):
        print(f"Server listening on ws://0.0.0.0:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())