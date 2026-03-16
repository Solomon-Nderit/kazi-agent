import pyautogui
import re
import time
import asyncio
import pyperclip

def normalized_to_coords(target):
    # Parses target as normalized coordinates (y, x) scaled 0-1000
    nums = re.findall(r'\d+', str(target))
    if len(nums) >= 2:
        y_norm = int(nums[0])
        x_norm = int(nums[1])
    else:
        raise ValueError(f"Could not parse normalized coordinates from target: {target}")

    screen_width, screen_height = pyautogui.size()
    
    x = int((x_norm / 1000.0) * screen_width)
    y = int((y_norm / 1000.0) * screen_height)

    return x, y


async def type_text_interruptible(text, state_obj):
    """Types text character by character so it can be interrupted."""
    for char in text:
        if state_obj:
            if state_obj.abort_flag.is_set():
                raise asyncio.CancelledError("Action aborted by user.")
            while state_obj.is_paused:
                await asyncio.sleep(0.1)
        pyautogui.write(char)
        await asyncio.sleep(0.01)

async def wait_interruptible(seconds, state_obj):
    """Waits in tiny chunks to allow immediate interruption."""
    chunks = int(seconds / 0.1)
    for _ in range(chunks):
        if state_obj:
            if state_obj.abort_flag.is_set():
                raise asyncio.CancelledError("Action aborted by user.")
            while state_obj.is_paused:
                await asyncio.sleep(0.1)
        await asyncio.sleep(0.1)

async def take_action(actions=None, state_obj=None, **kwargs):
    if actions is None: 
        actions = kwargs
    action = actions.get('action') or kwargs.get('action')
    value = actions.get('value') or kwargs.get('value', '')

    valid_actions = [
        'click', 'move_mouse_and_click', 'click_and_type', 'click_and_type_text', 
        'click_and_drag', 'type_text', 'press_key', 'press_keyboard_key', 'double_click', 'right_click', 
        'hotkey', 'scroll', 'wait'
    ]
    if action not in valid_actions:
        raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}.")

    if action in ['click', 'move_mouse_and_click']:
        target = normalized_to_coords(actions['target'])
        pyautogui.moveTo(target[0], target[1], duration=0.5)
        pyautogui.click()

    elif action == 'click_and_drag':
        start_target = normalized_to_coords(actions['target'])
        end_target = normalized_to_coords(actions['end_target'])
        
        # 1. Move and click FIRST to ensure the window and text area are focused
        pyautogui.moveTo(start_target[0], start_target[1], duration=0.2)
        pyautogui.click()
        await asyncio.sleep(0.3) # Wait for Windows to bring the app to the foreground
        
        # 2. Perform the actual drag
        pyautogui.mouseDown(button='left')
        await asyncio.sleep(0.2)
        pyautogui.moveTo(end_target[0], end_target[1], duration=1.0) 
        await asyncio.sleep(0.1)
        pyautogui.mouseUp(button='left')

    elif action in ['click_and_type', 'click_and_type_text']:
        target = normalized_to_coords(actions['target'])
        pyautogui.moveTo(target[0], target[1], duration=0.5)
        pyautogui.click()
        await type_text_interruptible(value, state_obj)

    elif action == 'type_text':
        await type_text_interruptible(value, state_obj)

    elif action in ['press_key', 'press_keyboard_key']:
        if value not in pyautogui.KEYBOARD_KEYS:
            raise ValueError(f"Invalid key '{value}'. Key must be a valid PyAutoGUI key (e.g., 'enter', 'win', 'esc', 'tab').")
        pyautogui.press(value)

    elif action == 'double_click':
        target = normalized_to_coords(actions['target'])
        pyautogui.moveTo(target[0], target[1], duration=0.5)
        pyautogui.doubleClick()

    elif action == 'right_click':
        target = normalized_to_coords(actions['target'])
        pyautogui.moveTo(target[0], target[1], duration=0.5)
        pyautogui.rightClick()

    elif action == 'hotkey':
        # value should be a comma separated list of keys e.g. "ctrl, c" or "win, r"
        keys = [k.strip() for k in value.split(',')]
        for k in keys:
            if k not in pyautogui.KEYBOARD_KEYS:
                 raise ValueError(f"Invalid hotkey part '{k}'. Must be a valid PyAutoGUI key.")
        pyautogui.hotkey(*keys)

    elif action == 'scroll':
        # value should be the amount to scroll (positive up, negative down)
        try:
            scroll_amount = int(value)
            pyautogui.scroll(scroll_amount)
        except ValueError:
             raise ValueError(f"Scroll value must be an integer, got: {value}")
             
    elif action == 'wait':
        # value should be seconds to wait
        try:
            wait_amount = float(value)
            await wait_interruptible(wait_amount, state_obj)
        except ValueError:
             raise ValueError(f"Wait value must be a number (seconds), got: {value}")

async def execute_pc_action(action: str, state_obj=None, target: str = "", value: str = "", end_target: str = "") -> dict:
    """Executes a PC automation action on the user's screen.
    
    Args:
        action: The type of action to perform.
        target: The grid coordinate label (e.g., '500, 500'). 
        value: The text to type or the keyboard key to press. 
        end_target: The end coordinate grid label for dragging.
    """
    actions_dict = {'action': action}
    if target: 
        actions_dict['target'] = target
    if value: 
        actions_dict['value'] = value
    if end_target:
        actions_dict['end_target'] = end_target

    print(f"\n[SYSTEM] Executing local action: {actions_dict}")
    try:
        await take_action(actions_dict, state_obj=state_obj)
        return {"status": "success", "message": f"Successfully performed {action}."}
    except Exception as e:
        return {"status": "error", "message": f"Failed due to error: {str(e)}"}