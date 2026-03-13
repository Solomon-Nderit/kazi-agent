from action import take_action
from screenshot import get_screen_with_grid

import requests
import re

import cv2

url = "http://127.0.0.1:8000/predict/"







def send_image():
    images = get_screen_with_grid()

    payload = images[1]

    # 1. Encode the numpy array to an image format (like PNG)
    success, encoded_image = cv2.imencode('.png', payload)
    image_bytes = encoded_image.tobytes()

    response = requests.post(url, files={"file": ("screenshot.png", image_bytes, "image/png")})

    return response

# response=requests.get(url)
def get_actions(ai_response):
    pattern = r"{(.*?)}"

    matches = re.findall(pattern, ai_response.text)
    instructions = []


    for i in matches:
        # Use .strip() to remove spaces and quotes from both the key and the value
        my_dict = {
            key.strip(" '\""): value.strip(" '\"") 
            for item in i.split(',') 
            for key, value in [item.split(':')]
        }
        instructions.append(my_dict)

    return instructions

# def carry_out_actions():
#     actions = [{'action': 'click', 'target': 'BL10'}]

#     for i in actions:
#         take_action(i)


# carry_out_actions()

response = send_image()
print(response.text)