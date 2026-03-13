from action import take_action
from screenshot import get_screen_with_grid

import requests
import re
import json
import numpy as np
import io
import cv2

url = "http://127.0.0.1:8000/predict/"







def send_image():
    images = get_screen_with_grid()

    payload = images[1]

    payload_rgb = cv2.cvtColor(payload, cv2.COLOR_BGR2RGB)


    buffer = io.BytesIO()
    np.save(buffer, payload_rgb)
    image_bytes = buffer.getvalue()

    response = requests.post(
        url, 
        files={"file": ("screenshot.npy", image_bytes, "application/octet-stream")},
        data={"instruction": "open msedge"}
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
    


# def carry_out_actions():
#     actions = [{'action': 'click', 'target': 'BL10'}]

#     for i in actions:
#         take_action(i)


# carry_out_actions()

response = send_image()
actions = get_actions(response)
print(actions)