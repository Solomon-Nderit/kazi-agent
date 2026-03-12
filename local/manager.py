import time
import cv2
import json
import base64
import keyboard
import requests
import numpy as np
import speech_recognition as sr
from uuid import uuid4

# Import your custom modules
from screenshot import get_screen_with_grid
from action import execute_actions

CLOUD_ENDPOINT = "http://127.0.0.1:8000/api/predict" # Change to Cloud Run URL in production

# Development option: Set to True to type commands instead of using voice input
USE_TYPED_INPUT = True

def get_typed_intent() -> str:
    """Uses standard input to get initial instruction from the user."""
    try:
        intent = input("⌨️ Enter your objective (press Enter to submit): ")
        if not intent.strip():
            return None
        print(f"✅ Intent captured: '{intent}'")
        return intent
    except Exception as e:
        print(f"❌ Error getting input: {e}")
        return None

def get_audio_intent() -> str:
    """Uses microphone to get initial instruction from the user."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Listening for objective... Speak now.")
        audio = recognizer.listen(source, timeout=10)
    try:
        intent = recognizer.recognize_google(audio)
        print(f"✅ Intent captured: '{intent}'")
        return intent
    except sr.UnknownValueError:
        print("❌ Could not understand audio. Aborting.")
        return None

def encode_image(img_array: np.ndarray) -> str:
    """Converts OpenCV BGR image into base64 string for HTTP transmission."""
    # Encode as WebP with 95% quality. WebP preserves sharp UI text and grid edges 
    # vastly better than JPEG, while keeping payload size small for API limits.
    _, buffer = cv2.imencode('.webp', img_array, [cv2.IMWRITE_WEBP_QUALITY, 95])
    return base64.b64encode(buffer).decode('utf-8')

def wait_for_ui_stability(step_size: int, delay=0.0001, threshold=2.0) -> np.ndarray:
    """
    Prevents screenshotting during UI animations (scrolling, page loading).
    Snaps greyscale low-res versions and checks Mean Squared Error pixel differences.
    Returns the high-res stabilized frame.
    """
    print("⏳ Waiting for UI stability...")
    raw1, _ = get_screen_with_grid(step_size=step_size)
    gray1 = cv2.cvtColor(raw1, cv2.COLOR_BGR2GRAY)
    
    while True:
        time.sleep(delay)
        raw2, overlayed = get_screen_with_grid(step_size=step_size)
        gray2 = cv2.cvtColor(raw2, cv2.COLOR_BGR2GRAY)
        
        # Calculate MSE (Mean Squared Error) between frames
        err = np.sum((gray1.astype("float") - gray2.astype("float")) ** 2)
        err /= float(gray1.shape[0] * gray1.shape[1])
        
        if err < threshold:
            print("🛑 UI is stable. Capturing state.")
            return raw2, overlayed
            
        gray1 = gray2 # Keep rolling forward

def execute_visual_loop(intent: str):
    session_id = str(uuid4())
    print(f"\n--- Starting UI Execution Loop | Session: {session_id} ---")
    
    # Grid size parameter matching your parser. Smaller = higher resolution tracking but harder LLM reads.
    GRID_STEP_SIZE = 50 
    
    while True:
        # 1. Capture visual context only once UI stops moving
        raw_img, grid_img = wait_for_ui_stability(step_size=GRID_STEP_SIZE)
        
        # 2. Package and dispatch
        payload = {
            "session_id": session_id,
            "intent": intent,
            "grid_image_b64": encode_image(grid_img)
        }
        
        print("☁️ Calling Cloud Brain...")
        response = requests.post(CLOUD_ENDPOINT, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Server Error: {response.text}")
            break
            
        data = response.json()
        print(f"\n🧠 Cloud Reasoning: {data['reasoning']}")
        print(f"📦 Cloud Actions: {data['actions']}")
        
        if data['status'] == "COMPLETED":
            print("\n✅ Goal accomplished. Halting loop.")
            # Trigger audio sound here: "Objective complete"
            break
            
        if data['status'] == "REQUIRES_HUMAN":
            print("\n⚠️ LLM detected blocker (e.g., OTP or physical barrier). Taking over locally required.")
            break
            
        # 3. Fire the Muscle layer using your written code
        print("🤖 Physical Execution Commencing...")
        execute_actions(data['actions'], step_size=GRID_STEP_SIZE)

# Setup hotkey binder (requires admin rights on Windows)
def on_hotkey_press():
    print("\n--- Agent Triggered ---")
    if USE_TYPED_INPUT:
        intent = get_typed_intent()
    else:
        intent = get_audio_intent()
        
    if intent:
        execute_visual_loop(intent)

print(f"Kazi Local Daemon running. Input mode: {'TYPING' if USE_TYPED_INPUT else 'VOICE'}. Press CTRL+ALT+A to activate Agent.")
keyboard.add_hotkey('ctrl+alt+a', on_hotkey_press)
keyboard.wait()