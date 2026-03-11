from pynput.mouse import Button, Controller as mouse_controller
from pynput.keyboard import Key, Controller as key_controller



mouse = mouse_controller()
keyboard = key_controller()

import time
import re

def parse_grid_coordinate(coord_str: str, step_size: int = 50) -> tuple:
    """Translates a grid coordinate like 'A1' or 'B2' into a pixel (x, y) center."""
    match = re.match(r"([A-Z]+)(\d+)", coord_str.upper())
    if not match:
        return None
    
    cols_str, row_str = match.groups()
    
    # Convert column string to index (A=0, B=1, ..., Z=25, AA=26)
    col_idx = 0
    for char in cols_str:
        col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
    col_idx -= 1 # 0-indexed
    
    row_idx = int(row_str) - 1 # 0-indexed
    
    # Calculate pixel coordinates for the center of the grid square
    x = col_idx * step_size + step_size // 2
    y = row_idx * step_size + step_size // 2
    return (x, y)

def execute_actions(actions_list: list, step_size: int = 50):
    """Executes a batch list of action dictionaries sequentially."""
    for cmd in actions_list:
        action = cmd.get("action")
        target = cmd.get("target")
        value = cmd.get("value")
        
        # 1. Move the mouse if a target grid coordinate is provided
        if target:
            pixel_coord = parse_grid_coordinate(target, step_size)
            if pixel_coord:
                mouse.position = pixel_coord
                time.sleep(0.1)  # small delay for cursor to register movement

        # 2. Execute the action
        if action == "click":
            mouse.click(Button.left)
        elif action == "right_click":
            mouse.click(Button.right)
        elif action == "double_click":
            mouse.click(Button.left, 2)
        elif action == "type":
            if value is not None:
                keyboard.type(str(value))
        elif action == "click_and_type":
            mouse.click(Button.left)
            time.sleep(0.1)
            if value is not None:
                keyboard.type(str(value))
        elif action == "hotkey":
            # Simple hotkey parser supporting e.g., "ctrl+c" or "enter"
            if value:
                keys_to_press = []
                for k in value.split('+'):
                    k = k.strip().lower()
                    
                    # Map common names to pynput Key names
                    if k == 'win':
                        k = 'cmd'
                    elif k == 'return':
                        k = 'enter'
                    
                    if hasattr(Key, k):
                        keys_to_press.append(getattr(Key, k))
                    else:
                        keys_to_press.append(k) # literal char
                
                for k in keys_to_press:
                    keyboard.press(k)
                for k in reversed(keys_to_press):
                    keyboard.release(k)
        elif action == "wait":
            if value:
                time.sleep(float(value))
                
        # Small pause between batch actions to let UI respond
        time.sleep(0.5)

# Example Usage (Batching Actions):
my_actions = [
    {"action": "click_and_type", "target": "C5", "value": "Hello World!"},
    {"action": "hotkey", "value": "enter"}
]

# execute_actions(my_actions)
