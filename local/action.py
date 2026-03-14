import pyautogui
import re


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


def take_action(actions):
    action = actions.get('action')
    value = actions.get('value', '')

    valid_actions = ['click', 'move_mouse_and_click', 'click_and_type', 'click_and_type_text', 'press_key', 'press_keyboard_key']
    if action not in valid_actions:
        raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}.")

    if action in ['click', 'move_mouse_and_click']:
        target = normalized_to_coords(actions['target'])
        pyautogui.moveTo(target)
        pyautogui.click()

    elif action in ['click_and_type', 'click_and_type_text']:
        target = normalized_to_coords(actions['target'])
        pyautogui.moveTo(target)
        pyautogui.click()
        pyautogui.typewrite(value)

    elif action in ['press_key', 'press_keyboard_key']:
        if value not in pyautogui.KEYBOARD_KEYS:
            raise ValueError(f"Invalid key '{value}'. Key must be a valid PyAutoGUI key (e.g., 'enter', 'win', 'esc', 'tab').")
        pyautogui.press(value)

def execute_pc_action(action: str, target: str = "", value: str = "") -> dict:
    """Executes a PC automation action on the user's screen.
    
    Args:
        action: The type of action to perform. Must be one of: 'click', 'click_and_type', 'press_key'.
        target: The grid coordinate label (e.g., 'A1', 'C5'). Leave empty if not applicable.
        value: The text to type or the keyboard key to press. Leave empty if not applicable.
    """
    # Repackage the arguments into the dictionary your original function expects
    actions_dict = {'action': action}
    if target: 
        actions_dict['target'] = target
    if value: 
        actions_dict['value'] = value

    print(f"\n[SYSTEM] Executing local action: {actions_dict}")
    try:
        take_action(actions_dict) # This calls your existing pyautogui logic
        return {"status": "success", "message": f"Successfully performed {action}."}
    except Exception as e:
        return {"status": "error", "message": f"Failed due to error: {str(e)}"}