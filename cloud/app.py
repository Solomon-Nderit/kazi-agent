from PIL import Image
from google import genai
from google.genai import types

from dotenv import load_dotenv
import io
import numpy as np

from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel






app = FastAPI()



load_dotenv()

client = genai.Client()


def get_response(image, instruction: str) -> str:
    image = Image.fromarray(np.load(io.BytesIO(image)))
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[image, f"If you were to be instructed to '{instruction}' by the user of the computer shown in the image, how would you go about it? Your response should be strictly a json output containing only the next logical action. "
    "It should look like this: {'action': 'action goes here' , 'target': 'the cell to be targeted', 'value':'the value to type or the key to click'}. In case of moving the mouse, you would output something like this: "
    "{'action':'click', 'target':'C5'}. In case you also wanted to type, the value would be this: {'action':'click_and_type', 'target':'C5', 'value':'Hello World'}. If you want to press a specific key on the keyboard, like Enter, output: {'action': 'press_key', 'value': 'enter'}. If the task is fully completed, output: {'action': 'done'}. "],
    
)
    return response.text


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/predict/")
async def create_upload_file(file: UploadFile = File(...), instruction: str = Form(...)):
    # Read the image bytes
    image_data = await file.read()

    response = get_response(image_data, instruction)
    
    # Example: Return file metadata and size
    return response