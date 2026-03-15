from typing import Literal

def execute_pc_action(action: Literal['click', 'double_click', 'right_click', 'click_and_type', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'], target: str = "", value: str = "") -> dict:
    """Executes a PC automation action on the user's screen.
    
    Args:
        action: The type of action to perform. Must be strictly one of: 'click', 'double_click', 'right_click', 'click_and_type', 'type_text', 'press_key', 'hotkey', 'scroll', 'wait'.
        target: The normalized y, x coordinates (e.g., '500, 500') scaled between 0 and 1000. Required for click/type actions.
        value: The text to type, keyboard key (e.g., 'enter', 'win'), hotkeys (e.g., 'ctrl, c'), scroll amount, or wait seconds. Required for non-click actions.
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

TOOLS = [execute_pc_action, request_screenshot, start_objective, pause_current_task, resume_current_task, finish_objective, abort_current_task]
