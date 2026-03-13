import pyautogui
import re


def label_to_coords(label, step_size=50):
    chars = re.findall(r'[A-Za-z]+|\d+', label)

    # print(chars)
    
    letter_part = chars[0].upper()
    number = int(chars[1])

    # Convert standard Excel-style column letters to a number (A=1, Z=26, AA=27)
    letter_index = 0
    for char in letter_part:
        # Multiply current total by 26 and add the character's value (A=1...Z=26)
        letter_index = letter_index * 26 + (ord(char) - 64)

    # print(f"Letter string: {letter_part}, Calculated Index: {letter_index}")

    x = (letter_index * step_size) - (step_size // 2)
    y = (number * step_size) - (step_size // 2)

    return x, y


def take_action(actions):
    action = actions['action']
    
    if actions.get('value'):
        value = actions['value']

    if action == 'click':
        target = label_to_coords(actions['target'])
        pyautogui.moveTo(target)
        pyautogui.click()

    elif action == "click_and_type":
        target = label_to_coords(actions['target'])
        pyautogui.moveTo(target)
        pyautogui.click()
        pyautogui.typewrite(value)

    elif action == "press_key":
        pyautogui.press(value)
