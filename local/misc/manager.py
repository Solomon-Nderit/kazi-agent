from action import take_action
from local.misc.screenshot import get_screen_with_grid

import requests
import re
import json
import numpy as np
import io
import cv2

import time

url = "http://127.0.0.1:8000/predict/"







def send_image(instruction):
    images = get_screen_with_grid()

    payload = images[1]

    payload_rgb = cv2.cvtColor(payload, cv2.COLOR_BGR2RGB)


    buffer = io.BytesIO()
    np.save(buffer, payload_rgb)
    image_bytes = buffer.getvalue()

    response = requests.post(
        url, 
        files={"file": ("screenshot.npy", image_bytes, "application/octet-stream")},
        data={"instruction": instruction}
    )

    return response

# response=requests.get(url)
def get_actions(ai_response):
     # Depending on how the API returns data, response.json() might be a string containing JSON
    try:
        # First parsing: get the string out of the requests response
        response_data = ai_response.json()
        
        # Strip markdown formatting if Gemini wrapped it in ```json ... ```
        if isinstance(response_data, str):
            response_data = response_data.strip()
            if response_data.startswith("```json"):
                response_data = response_data[7:]
            if response_data.startswith("```"):
                response_data = response_data[3:]
            if response_data.endswith("```"):
                response_data = response_data[:-3]
            response_data = response_data.strip()
            
            return [json.loads(response_data)]
        else:
            return [response_data]
            
    except json.JSONDecodeError:
        # Fallback if it's not strictly JSON, try ast.literal_eval or string manipulation
        import ast
        return [ast.literal_eval(ai_response.text.strip('"').replace('\\"', '"'))]
    


def carry_out_actions(instruction: str):
    while True:
        print("Taking screenshot and asking AI...")
        response = send_image(instruction)
        actions = get_actions(response)
        
        # In case our parsing failed or AI returned an empty list
        if not actions:
            print("No valid actions returned. Retrying after 2s...")
            time.sleep(2)
            continue
            
        action_dict = actions[0]
        action_type = action_dict.get('action')
        
        print(f"Executing: {action_dict}")
        
        if action_type == 'done':
            print("Task completed by AI!")
            break
            
        take_action(action_dict)
        
        print("Action taken! Waiting 3s for UI to settle...")
        time.sleep(3)


carry_out_actions("open edge browser and search for cats")

# response = send_image()
# actions = get_actions(response)
# print(actions)