from typing import Literal

def execute_pc_action(action: Literal['click', 'double_click', 'right_click', 'click_and_type', 'click_and_drag', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'], target: str = "", value: str = "", end_target: str = "") -> dict:
    """Executes a PC automation action on the user's screen.
    
    Args:
        action: The type of action to perform. Must be strictly one of: 'click', 'double_click', 'right_click', 'click_and_type', 'click_and_drag', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'.
        target: The normalized y, x coordinates (e.g., '500, 500') scaled between 0 and 1000. Required for click/type/drag actions.
        value: The text to type, keyboard key (e.g., 'enter', 'win'), hotkeys (e.g., 'ctrl, c'), scroll amount, or wait seconds. Required for non-click actions.
        end_target: The normalized y, x coordinates (e.g., '600, 600') scaled between 0 and 1000. Required ONLY for 'click_and_drag' action indicating where to release the mouse.
    """
    pass

def request_screenshot():
    """Takes a screenshot of the user's current screen and uploads it to your visual context so you can see the UI."""
    pass

def start_objective(description: str):
    """Starts a new background objective loop on the user's PC. Instead of micromanaging the workflow with immediate clicks, use this tool when the user asks you to complete a multi-step task.
    Args:
        description: A clear description of the ultimate goal you need to achieve.
    """
    pass

def pause_current_task():
    """Pauses the current background objective loop. Use this if you need to ask the user a verifying question before continuing (e.g. before sending an email or spending money), or if the user asks you to hold on."""
    pass

def resume_current_task():
    """Resumes the paused background objective loop."""
    pass

def finish_objective():
    """Declares the current multi-step objective completely finished. Always call this when you have completed what the user asked you to do in an objective loop."""
    pass

def abort_current_task():
    """Instantly cancels and aborts any active or queued physical PC actions (typing, moving, waiting) on the user's machine. 
    Use this immediately if the user asks you to stop, wait, pause, or freeze during an operation."""
    pass

def get_clipboard_content() -> str:
    """Reads the current text stored in the user's Windows clipboard. Use this after using 'click_and_drag' or hotkeys to copy text (ctrl, c) so you can read what was copied."""
    pass

def open_url(url: str):
    """Opens a website instantly in the user's default browser."""
    pass

def open_app(app_name: str):
    """Launches a common Windows application instantly (e.g., 'notepad', 'calc', 'excel', 'msedge')."""
    pass

def list_open_windows() -> str:
    """Returns a list of all currently open window titles on the screen. Use this instead of Alt-Tab to find an app."""
    pass

def focus_window(title: str):
    """Brings a specific window to the foreground instantly. Pass the exact title retrieved from list_open_windows()."""
    pass

TOOLS = [execute_pc_action, request_screenshot, start_objective, pause_current_task, resume_current_task, finish_objective, abort_current_task, get_clipboard_content, open_url, open_app, list_open_windows, focus_window]
