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

def abort_current_task():
    """Instantly cancels and aborts any active or queued physical PC actions (typing, moving, waiting) on the user's machine. 
    Use this immediately if the user asks you to stop, wait, pause, or freeze during an operation."""
    pass

TOOLS = [execute_pc_action, request_screenshot, abort_current_task]
