from typing import Literal

def execute_pc_action(action: Literal['click', 'double_click', 'right_click', 'click_and_type', 'click_and_drag', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'], target: str = "", value: str = "", end_target: str = "", **kwargs) -> dict:
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

def create_plan(objective: str, steps: list[str]):
    """Starts a new background objective loop on the user's PC. Use this to plan out a multi-step task before executing it.
    Args:
        objective: A clear description of the ultimate goal you need to achieve.
        steps: A list of string descriptions for each sequential step.
    """
    pass

def mark_step_complete(step_index: int):
    """Marks the current step as complete after you have visually verified it succeeded on the screen.
    Args:
        step_index: The index of the step you are marking complete.
    """
    pass

def mark_step_failed(step_index: int, reason: str):
    """Marks the current step as failed. Call this if an action isn't working after multiple tries and you need to rethink the plan.
    Args:
        step_index: The index of the failed step.
        reason: Why it failed.
    """
    pass

def pause_current_task():
    """Pauses the current background objective loop. Use this if you need to ask the user a verifying question before continuing, or wait for them to finish input."""
    pass

def resume_current_task():
    """Resumes the paused background objective loop."""
    pass

def abort_current_task():
    """Instantly cancels and aborts any active or queued physical PC actions. Use this immediately if the user asks you to stop/cancel."""
    pass

def get_clipboard_content() -> str:
    """Reads the current text stored in the user's Windows clipboard."""
    pass

def set_clipboard_content(text: str):
    """Writes text directly to the user's clipboard. Use this to easily copy code or answers for the user."""
    pass

def open_url(url: str):
    """Opens a website instantly in the user's default browser."""
    pass

def open_app(app_name: str):
    """Launches a common Windows application instantly (e.g., 'notepad', 'calc', 'excel', 'msedge')."""
    pass

def close_app(process_name: str):
    """Programmatically kills a running application (e.g., 'chrome.exe', 'notepad.exe')."""
    pass

def list_open_windows() -> str:
    """Returns a list of all currently open window titles on the screen."""
    pass

def focus_window(title: str):
    """Brings a specific window to the foreground instantly. Pass the exact title retrieved from list_open_windows()."""
    pass

def read_text_file(filepath: str) -> str:
    """Reads the contents of a text file from the user's system."""
    pass

def write_text_file(filepath: str, content: str):
    """Writes text content to a file on the user's system."""
    pass

def list_directory(filepath: str) -> str:
    """Lists all files and folders inside a given directory path."""
    pass

def run_shell_command(command: str) -> str:
    """Runs a shell/terminal command (Windows cmd) and returns the standard output. Restricted to 10 seconds."""
    pass

def fetch_webpage_text(url: str) -> str:
    """Extracts raw text content from a URL via a background HTTP request. Great for reading articles / docs without opening a browser."""
    pass

TOOLS = [
    execute_pc_action, request_screenshot, create_plan, mark_step_complete, mark_step_failed,
    pause_current_task, resume_current_task, abort_current_task, get_clipboard_content, 
    set_clipboard_content, open_url, open_app, close_app, list_open_windows, focus_window, 
    read_text_file, write_text_file, list_directory, run_shell_command, fetch_webpage_text
]
