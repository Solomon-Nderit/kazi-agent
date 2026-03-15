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
    "tools": TOOLS,
    # 1. Enable context window compression to allow infinite token sliding
    "context_window_compression": {"sliding_window": {}}
}

async def handle_client(websocket):
    print("Client connected!")
    previous_session_handle = None

    try:
        # Wrap the session in a while loop for Session Resumption
        while True:
            # 2. Inject previous handle if we have one
            current_config = CONFIG.copy()
            if previous_session_handle:
                current_config["session_resumption"] = {"handle": previous_session_handle}
                print(f"Resuming session from GoAway/Disconnect...")
            else:
                print("Starting new session...")

            try:
                async with client.aio.live.connect(model=MODEL, config=current_config) as session:
                    
                    async def receive_from_client():
                        async for message in websocket:
                            if isinstance(message, bytes):
                                await session.send_realtime_input(audio=types.Blob(data=message, mime_type="audio/pcm"))
                            else:
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
                                    
                                    if data.get("is_screenshot"):
                                        await asyncio.sleep(1.5)
                                        await session.send_realtime_input(
                                            text="System: The new screenshot is now in your visual context. Please analyze the grid and decide your next action or answer the user."
                                        )
                                elif "type" in data and data["type"] == "image":
                                    import base64
                                    img_bytes = base64.b64decode(data["data"])
                                    await session.send_realtime_input(
                                        video=types.Blob(data=img_bytes, mime_type="image/jpeg")
                                    )

                    async def receive_from_gemini():
                        nonlocal previous_session_handle
                        while True:
                            turn = session.receive()
                            async for response in turn:
                                # A. Check for resumption breadcrumbs
                                if getattr(response, "session_resumption_update", None):
                                    update = response.session_resumption_update
                                    if getattr(update, "resumable", False) and getattr(update, "new_handle", None):
                                        previous_session_handle = update.new_handle

                                # B. Capture GoAway signal
                                if getattr(response, "go_away", None):
                                    print("Server hit time limit. GoAway received. Reconnecting...")
                                    return # Exits the task gracefully

                                # C. Normal audio output
                                if getattr(response, "server_content", None) and getattr(response.server_content, "model_turn", None):
                                    for part in response.server_content.model_turn.parts:
                                        if getattr(part, "inline_data", None) and isinstance(part.inline_data.data, bytes):
                                            await websocket.send(part.inline_data.data)

                                # D. Tool Calls
                                if getattr(response, "tool_call", None):
                                    for function_call in response.tool_call.function_calls:
                                        await websocket.send(json.dumps({
                                            "type": "tool_call",
                                            "id": function_call.id,
                                            "name": function_call.name,
                                            "args": function_call.args
                                        }))

                    # Run both tasks until ONE finishes (meaning either websocket drops OR Gemini resets)
                    task_client = asyncio.create_task(receive_from_client())
                    task_gemini = asyncio.create_task(receive_from_gemini())

                    done, pending = await asyncio.wait(
                        [task_client, task_gemini], 
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Clean up the pending task completely so we don't leak sockets/memory
                    for task in pending:
                        task.cancel()

                    # Check if client completely disconnected
                    for task in done:
                        try:
                            task.result()
                        except websockets.exceptions.ConnectionClosed:
                            print("Client fully disconnected.")
                            return

            except websockets.exceptions.ConnectionClosed:
                print("Client disconnected.")
                break
            except Exception as e:
                print(f"Gemini connection interrupted: {e}. Reconnecting in background...")
                await asyncio.sleep(1)
                continue

    except Exception as e:
        print(f"Fatal Client Error: {e}")

async def main():
    # Cloud Run injects the PORT environment variable.
    # We fallback to 8765 for local testing if the var is missing.
    port = int(os.environ.get("PORT", 8765))
    
    async with websockets.serve(handle_client, "0.0.0.0", port):
        print(f"Server listening on ws://0.0.0.0:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())