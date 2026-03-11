from local.screenshot import get_screen_with_grid
from local.action import execute_actions


my_actions = [
    {"action": "click_and_type", "target": "C5", "value": "Hello World!"},
    {"action": "hotkey", "value": "enter"}
]

execute_actions(my_actions)