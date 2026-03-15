import asyncio
import websockets
import json
import base64
import keyboard
import pyperclip
import webbrowser
import os
import subprocess
try:
    import pygetwindow as gw
except ImportError:
    gw = None

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

async def execute_pc_action(action: str, target: str = "", value: str = "", end_target: str = "", abort_flag=None) -> dict:
    actions_dict = {'action': action}
    if target: actions_dict['target'] = target
    if value: actions_dict['value'] = value
    if end_target: actions_dict['end_target'] = end_target

    print(f"\n[SYSTEM] Executing local action: {actions_dict}")
    try:
        await take_action(actions_dict, abort_flag=abort_flag)
        return {"status": "success", "message": f"Successfully performed {action}."}
    except asyncio.CancelledError:
        print("[SYSTEM] Action aborted by user.")
        return {"status": "error", "message": "Action aborted by user."}
    except Exception as e:
        return {"status": "error", "message": f"Failed due to error: {str(e)}"}


class AgentState:
    def __init__(self):
        self.current_objective = None
        self.is_paused = False
        self.abort_flag = asyncio.Event()

    def abort(self):
        self.abort_flag.set()
        self.current_objective = None
        # We don't change pause state since aborting inherently stops the loop
    
    def reset(self):
        self.abort_flag.clear()
        self.is_paused = False

async def client_loop():
    # uri = "wss://kazi-copilot-brain-603050312015.us-central1.run.app"
    uri = " ws://localhost:8765"
    
    audio = AudioHandler()
    audio.start_playback()
    mic_stream = audio.start_recording()

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to cloud server...")
            
            state = AgentState()
            objective_task = None
            ready_for_next_step = asyncio.Event()
            ready_for_next_step.set()
            
            async def run_objective_loop():
                while state.current_objective:
                    if state.abort_flag.is_set():
                        break
                    if state.is_paused:
                        await asyncio.sleep(0.5)
                        continue
                        
                    await ready_for_next_step.wait()
                    ready_for_next_step.clear()

                    if state.abort_flag.is_set() or state.is_paused or not state.current_objective:
                        break

                    # Request next instruction using screenshot
                    print(f"\n[Objective Loop] Reporting state for objective: {state.current_objective}")
                    b64_img = await asyncio.to_thread(capture_screen_as_base64)
                    
                    await websocket.send(json.dumps({
                        "type": "image",
                        "data": b64_img
                    }))
                    
                    await websocket.send(json.dumps({
                        "type": "text",
                        "text": f"System Objective Engine: The current objective is '{state.current_objective}'. Above is the current screen. What is the EXACT NEXT STEP to achieve this objective? Remember if the objective is complete, you must explicitly tell me so we can end the loop."
                    }))
                    
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
                nonlocal objective_task
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Playback audio
                        if not state.abort_flag.is_set():
                            await asyncio.to_thread(audio.play_chunk, message)
                    else:
                        data = json.loads(message)
                        if data.get("type") == "tool_call":
                            name = data["name"]
                            args = data["args"]
                            call_id = data["id"]
                            
                            # Define what happens when tools complete to notify the objective loop
                            async def respond_and_trigger_next(result_dict, is_screenshot=False):
                                await websocket.send(json.dumps({
                                    "type": "tool_response",
                                    "id": call_id,
                                    "name": name,
                                    "response": result_dict,
                                    "is_screenshot": is_screenshot
                                }))
                                # If there's an objective running, let it know we finished a step
                                if state.current_objective and not state.is_paused and not state.abort_flag.is_set():
                                    if not is_screenshot: # screenshots trigger their own continuation
                                        await asyncio.sleep(2) # brief pause to let UI settle
                                        ready_for_next_step.set()

                            if name == "start_objective":
                                print(f"[SYSTEM] Starting new objective: {args.get('description')}")
                                state.reset()
                                state.current_objective = args.get("description")
                                if objective_task and not objective_task.done():
                                    objective_task.cancel()
                                ready_for_next_step.set()
                                objective_task = asyncio.create_task(run_objective_loop())
                                await respond_and_trigger_next({"status": "success", "message": "Objective loop started in background."})

                            elif name == "pause_current_task":
                                print("[SYSTEM] Pausing background task...")
                                state.is_paused = True
                                await respond_and_trigger_next({"status": "success", "message": "Loop paused."})

                            elif name == "resume_current_task":
                                print("[SYSTEM] Resuming background task...")
                                state.is_paused = False
                                ready_for_next_step.set()
                                await respond_and_trigger_next({"status": "success", "message": "Loop resumed."})

                            elif name == "abort_current_task":
                                print("[SYSTEM] ABORT ALL triggered!")
                                state.abort()
                                if objective_task: objective_task.cancel()
                                await respond_and_trigger_next({"status": "success", "message": "Task aborted."})

                            elif name == "finish_objective":
                                print("[SYSTEM] Objective completed!")
                                state.current_objective = None
                                if objective_task: objective_task.cancel()
                                await respond_and_trigger_next({"status": "success", "message": "Objective finished."})

                            elif name == "execute_pc_action":
                                # Run taking action as a background task to not block the socket
                                async def bg_execute():
                                    result = await execute_pc_action(abort_flag=state.abort_flag, **args)
                                    await respond_and_trigger_next(result)
                                asyncio.create_task(bg_execute())

                            elif name == "get_clipboard_content":
                                try:
                                    clipboard_text = pyperclip.paste()
                                    await respond_and_trigger_next({"content": clipboard_text})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": f"Failed to read clipboard: {str(e)}"})

                            elif name == "open_url":
                                url = args.get("url", "")
                                if url:
                                    print(f"[SYSTEM] Opening URL: {url}")
                                    webbrowser.open(url)
                                    await respond_and_trigger_next({"status": "success", "message": f"Opened {url}"})
                                else:
                                    await respond_and_trigger_next({"error": "No URL provided."})

                            elif name == "open_app":
                                app_name = args.get("app_name", "")
                                if app_name:
                                    print(f"[SYSTEM] Opening App: {app_name}")
                                    subprocess.Popen(f"start {app_name}", shell=True)
                                    await respond_and_trigger_next({"status": "success", "message": f"Launched {app_name}"})
                                else:
                                    await respond_and_trigger_next({"error": "No app_name provided."})

                            elif name == "list_open_windows":
                                if gw:
                                    # Filter out empty or invisible titles
                                    windows = [w.title for w in gw.getAllWindows() if w.title and w.visible]
                                    await respond_and_trigger_next({"windows": windows})
                                else:
                                    await respond_and_trigger_next({"error": "pygetwindow is not installed/supported."})

                            elif name == "focus_window":
                                title = args.get("title", "")
                                if gw and title:
                                    windows = gw.getWindowsWithTitle(title)
                                    if windows:
                                        try:
                                            windows[0].activate()
                                            await respond_and_trigger_next({"status": "success", "message": f"Focused window: {title}"})
                                        except Exception as e:
                                            await respond_and_trigger_next({"error": f"Failed to focus window: {str(e)}"})
                                    else:
                                        await respond_and_trigger_next({"error": f"No window found matching title: {title}"})
                                else:
                                    await respond_and_trigger_next({"error": "Missing title or pygetwindow not installed."})
                            
                            elif name == "request_screenshot":
                                print("Taking screenshot...")
                                b64_img = await asyncio.to_thread(capture_screen_as_base64)
                                await websocket.send(json.dumps({
                                    "type": "image",
                                    "data": b64_img
                                }))
                                await respond_and_trigger_next({
                                    "status": "success", 
                                    "message": "Screenshot uploaded. System will auto-prompt."
                                }, is_screenshot=True)

            await asyncio.gather(send_audio(), send_text_cli(), receive_messages())

    except Exception as e:
        print(f"Disconnected: {e}")
    finally:
        audio.close()

if __name__ == "__main__":
    asyncio.run(client_loop())