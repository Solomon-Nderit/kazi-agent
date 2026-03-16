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
        self.plan_objective = None
        self.plan_steps = []
        self.current_step_index = 0
        self.loop_phase = 'idle' # 'idle', 'planning', 'executing', 'verifying'
        
        self.is_paused = False
        self.abort_flag = asyncio.Event()

    def abort(self):
        self.abort_flag.set()
        self.plan_objective = None
        self.plan_steps = []
        self.current_step_index = 0
        self.loop_phase = 'idle'
    
    def reset(self):
        self.abort_flag.clear()
        self.is_paused = False
        self.plan_objective = None
        self.plan_steps = []
        self.current_step_index = 0
        self.loop_phase = 'idle'

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
                while state.plan_objective and state.current_step_index < len(state.plan_steps):
                    if state.abort_flag.is_set():
                        break
                    if state.is_paused:
                        await asyncio.sleep(0.5)
                        continue
                        
                    await ready_for_next_step.wait()
                    ready_for_next_step.clear()

                    if state.abort_flag.is_set() or state.is_paused or not state.plan_objective:
                        break
                    
                    if state.current_step_index >= len(state.plan_steps):
                        break
                    
                    current_step_desc = state.plan_steps[state.current_step_index]

                    print(f"\n[Objective Loop] Phase: {state.loop_phase} | Step {state.current_step_index + 1}/{len(state.plan_steps)}: {current_step_desc}")
                    b64_img = await asyncio.to_thread(capture_screen_as_base64)
                    
                    await websocket.send(json.dumps({
                        "type": "image",
                        "data": b64_img
                    }))

                    # Give Gemini's backend a sec to ingest the frame
                    await asyncio.sleep(1.0)
                    
                    if state.loop_phase == 'executing':
                        prompt = f"System Objective Engine: The overall objective is '{state.plan_objective}'. We are currently on Step {state.current_step_index + 1}: '{current_step_desc}'. Above is the current screen. Achieve this specific step using your PC tools. Do NOT attempt subsequent steps. If the step is already complete, call mark_step_complete()."
                    elif state.loop_phase == 'verifying':
                        prompt = f"System Verification Engine: You just attempted Step {state.current_step_index + 1}: '{current_step_desc}'. Look at the visual screen state. Did the action succeed? If yes, call mark_step_complete(). If it failed or needs another action, explain why and issue the next execute_pc_action to try again. If it is hopelessly stuck, call mark_step_failed()."
                    else:
                        prompt = "System: Awaiting next command."
                    
                    await websocket.send(json.dumps({
                        "type": "text",
                        "text": prompt
                    }))
                
                if state.plan_objective and state.current_step_index >= len(state.plan_steps):
                    print(f"\n[SYSTEM] Objective '{state.plan_objective}' finished entirely.")
                    state.reset()
                    
            agent_active = False

            async def send_audio():
                while True:
                    data = await asyncio.to_thread(mic_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                    if agent_active:
                        await websocket.send(data)

            async def send_text_cli():
                nonlocal agent_active
                print("[SYSTEM] Agent running in passive mode. Press Ctrl+Alt+A to activate listening.")
                while True:
                    await asyncio.sleep(0.1)
                    if keyboard.is_pressed('ctrl+alt+a'):
                        await asyncio.sleep(0.5)
                        agent_active = not agent_active
                        if agent_active:
                            print("[SYSTEM] Agent ACTIVATED. Listening...")
                            # Optionally take a screenshot upon activation for context
                            b64_img = await asyncio.to_thread(capture_screen_as_base64)
                            await websocket.send(json.dumps({
                                "type": "image",
                                "data": b64_img
                            }))
                            await websocket.send(json.dumps({
                                "type": "text",
                                "text": "System: The user has activated the agent. I am now listening. Here is a screenshot of my current screen."
                            }))
                        else:
                            print("[SYSTEM] Agent DEACTIVATED. Passive mode.")

                    if keyboard.is_pressed('ctrl+alt+v'):
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
                            async def respond_and_trigger_next(result_dict, is_screenshot=False, bypass_trigger=False):
                                await websocket.send(json.dumps({
                                    "type": "tool_response",
                                    "id": call_id,
                                    "name": name,
                                    "response": result_dict,
                                    "is_screenshot": is_screenshot
                                }))
                                # If there's an objective running, let it know we finished a step
                                if state.plan_objective and not state.is_paused and not state.abort_flag.is_set():
                                    if not is_screenshot and not bypass_trigger: # screenshots trigger their own continuation
                                        # If the tool wasn't a verification tool itself, advance to verification phase
                                        if name not in ["mark_step_complete", "mark_step_failed", "create_plan"]:
                                            state.loop_phase = 'verifying'
                                        
                                        await asyncio.sleep(3) # brief pause to let UI settle
                                        ready_for_next_step.set()

                            if name == "create_plan":
                                print(f"[SYSTEM] Agent generated a plan for: {args.get('objective')}")
                                print(f"[SYSTEM] Steps: {args.get('steps')}")
                                state.reset()
                                state.plan_objective = args.get("objective")
                                state.plan_steps = args.get("steps", [])
                                state.current_step_index = 0
                                state.loop_phase = 'executing'
                                
                                if objective_task and not objective_task.done():
                                    objective_task.cancel()
                                
                                objective_task = asyncio.create_task(run_objective_loop())
                                await respond_and_trigger_next({"status": "success", "message": "Plan accepted. Objective loop starting."}, bypass_trigger=False)

                            elif name == "mark_step_complete":
                                print(f"[SYSTEM] Step {state.current_step_index + 1} completed!")
                                state.current_step_index += 1
                                state.loop_phase = 'executing'
                                await respond_and_trigger_next({"status": "success", "message": "Step marked complete. Proceeding to next step."}, bypass_trigger=False)
                            
                            elif name == "mark_step_failed":
                                reason = args.get('reason', 'Unknown')
                                print(f"[SYSTEM] Step failed! Reason: {reason}")
                                state.loop_phase = 'idle'
                                state.plan_objective = None
                                await respond_and_trigger_next({"status": "success", "message": "Loop halted. Awaiting your new plan."})

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
                                state.reset()
                                if objective_task: objective_task.cancel()
                                await respond_and_trigger_next({"status": "success", "message": "Objective finished."})

                            elif name == "execute_pc_action":
                                # Run taking action as a background task to not block the socket
                                async def bg_execute():
                                    result = await execute_pc_action(abort_flag=state.abort_flag, **args)
                                    # Manually set phase and trigger next step since bypass_trigger=True below
                                    if state.plan_objective and not state.is_paused and not state.abort_flag.is_set():
                                        state.loop_phase = 'verifying'
                                        await asyncio.sleep(2) # brief pause to let UI settle
                                        ready_for_next_step.set()

                                # Instantly satisfy Gemini's turn so it resumes listening
                                await asyncio.sleep(0.5)
                                await respond_and_trigger_next({"status": "Started tool execution in background..."}, bypass_trigger=True)
                                asyncio.create_task(bg_execute())

                            elif name == "get_clipboard_content":
                                try:
                                    clipboard_text = pyperclip.paste()
                                    await respond_and_trigger_next({"content": clipboard_text})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": f"Failed to read clipboard: {str(e)}"})

                            elif name == "set_clipboard_content":
                                text = args.get("text", "")
                                try:
                                    pyperclip.copy(text)
                                    await respond_and_trigger_next({"status": "success", "message": "Copied to clipboard."})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": f"Failed to set clipboard: {str(e)}"})

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

                            elif name == "close_app":
                                process_name = args.get("process_name", "")
                                if process_name:
                                    print(f"[SYSTEM] Closing App: {process_name}")
                                    os.system(f"taskkill /f /im {process_name}")
                                    await respond_and_trigger_next({"status": "success", "message": f"Killed {process_name}"})
                                else:
                                    await respond_and_trigger_next({"error": "No process_name provided."})

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
                            
                            elif name == "read_text_file":
                                filepath = args.get("filepath", "")
                                try:
                                    with open(filepath, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    await respond_and_trigger_next({"content": content})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": str(e)})

                            elif name == "write_text_file":
                                filepath = args.get("filepath", "")
                                content = args.get("content", "")
                                try:
                                    with open(filepath, 'w', encoding='utf-8') as f:
                                        f.write(content)
                                    await respond_and_trigger_next({"status": "success", "message": f"Wrote to {filepath}"})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": str(e)})

                            elif name == "list_directory":
                                filepath = args.get("filepath", ".")
                                try:
                                    items = os.listdir(filepath)
                                    await respond_and_trigger_next({"items": items})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": str(e)})

                            elif name == "run_shell_command":
                                command = args.get("command", "")
                                try:
                                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                                    output = result.stdout if result.returncode == 0 else result.stderr
                                    await respond_and_trigger_next({"output": output, "returncode": result.returncode})
                                except subprocess.TimeoutExpired:
                                    await respond_and_trigger_next({"error": "Command timed out after 10 seconds."})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": str(e)})
                            
                            elif name == "fetch_webpage_text":
                                url = args.get("url", "")
                                try:
                                    import urllib.request
                                    from html.parser import HTMLParser

                                    class MLStripper(HTMLParser):
                                        def __init__(self):
                                            super().__init__()
                                            self.reset()
                                            self.strict = False
                                            self.convert_charrefs = True
                                            self.text = []
                                        def handle_data(self, d):
                                            self.text.append(d)
                                        def get_data(self):
                                            return ''.join(self.text)

                                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                                    with urllib.request.urlopen(req, timeout=10) as response:
                                        html = response.read().decode('utf-8')
                                        s = MLStripper()
                                        s.feed(html)
                                        text = s.get_data()
                                        # truncate to 30k chars to avoid blowing up context
                                        await respond_and_trigger_next({"text": text[:30000]})
                                except Exception as e:
                                    await respond_and_trigger_next({"error": str(e)})
                            
                            elif name == "request_screenshot":
                                print("Taking screenshot...")
                                b64_img = await asyncio.to_thread(capture_screen_as_base64)
                                
                                await respond_and_trigger_next({
                                    "status": "success",
                                    "message": "Screenshot uploaded. System will auto-prompt."
                                }, is_screenshot=True)

                                # Crucial: Let the tool turn close on Gemini's backend before bombarding frames
                                await asyncio.sleep(1.0)

                                await websocket.send(json.dumps({
                                    "type": "image",
                                    "data": b64_img
                                }))

            await asyncio.gather(send_audio(), send_text_cli(), receive_messages())

    except Exception as e:
        print(f"Disconnected: {e}")
    finally:
        audio.close()

if __name__ == "__main__":
    asyncio.run(client_loop())