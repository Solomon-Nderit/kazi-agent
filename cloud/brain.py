import os
import base64
from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from google import genai
from google.genai import types

# Define your exact API data constraints based on the `action.py` code
class ExecuteAction(BaseModel):
    action: str = Field(description="Must be exactly: click, right_click, double_click, type, click_and_type, hotkey, or wait")
    target: Optional[str] = Field(description="Alphanumeric grid block (e.g., 'C4'). ONLY USE THIS if an element click is required. Null otherwise.")
    value: Optional[str] = Field(description="Text string to type if action involves typing. Null otherwise.")

class GeminiDecision(BaseModel):
    reasoning: str = Field(description="Brief internal monologue of what UI elements you observed and what you plan to do next.")
    status: str = Field(description="Current status constraint: PROGRESS, COMPLETED, or REQUIRES_HUMAN")
    actions: List[ExecuteAction] = Field(description="Batch ordered sequence of system OS tasks required to advance the UI.")

app = FastAPI(title="Kazi Copilot Orchestrator")
ai_client = genai.Client() # Assumes GOOGLE_API_KEY environment variable is set

# In-Memory Session Storage
# Maps: { "uuid-string": {"goal": "text", "ledger": ["Action 1", "Action 2"]} }
ACTIVE_SESSIONS = {}

# Pydantic schemas for the inbound HTTP data
class InboundPayload(BaseModel):
    session_id: str
    intent: str
    grid_image_b64: str

# Optional GCP requirement mechanism 
def upload_audit_trail_gcs(session_id: str, step_count: int, img_b64: str, decision: GeminiDecision):
    """
    Executes entirely in the background off the main latency loop. Fulfills the 
    Google Cloud Project (GCP) hackathon mandate for enterprise observability.
    """
    from google.cloud import storage
    try:
        # Example Implementation - uncomment once GCP IAM role is connected
        # client = storage.Client()
        # bucket = client.bucket("kazi-visual-audit-logs")
        # 
        # decoded_img = base64.b64decode(img_b64)
        # blob = bucket.blob(f"{session_id}/step_{step_count}.jpg")
        # blob.upload_from_string(decoded_img, content_type="image/jpeg")
        # 
        # log_blob = bucket.blob(f"{session_id}/step_{step_count}.json")
        # log_blob.upload_from_string(decision.model_dump_json(), content_type="application/json")
        pass
    except Exception as e:
        print(f"GCS Upload Failed: {e}")

@app.post("/api/predict")
async def process_visual_loop(payload: InboundPayload, bg_tasks: BackgroundTasks):
    
    # Initialize Context/Session Ledger Memory
    if payload.session_id not in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[payload.session_id] = {
            "goal": payload.intent,
            "ledger": ["Initiated visual agent sequence."]
        }
    
    session = ACTIVE_SESSIONS[payload.session_id]
    
    # Dynamically inject the Text Ledger narrative logic so the LLM remembers where it is.
    ledger_str = "\n".join([f"- {item}" for item in session['ledger']])
    system_instruction = f"""
    You are an autonomous Desktop OS Navigation agent driving mouse and keyboard APIs directly.
    You view the user's monitor entirely through a generated visual alpha-numeric coordinate grid.

    GLOBAL OBJECTIVE: {session['goal']}
    
    YOUR MEMORY LEDGER (ACTIONS COMPLETED SO FAR IN PREVIOUS STEPS):
    {ledger_str}
    
    DIRECTIONS:
    1. Look at the attached newly arrived gridded screen image. Identify if the outcome of the LAST ledger item was successful.
    2. Identify the very next physical elements necessary to progress the objective. 
    3. Generate the absolute minimal, batch execution chain using the allowed 'action' parameters. Map targets strictly to the overlaid letter-number boxes.
    """

    # Format the payload for Gemini strictly typed parsing 
    prompt =[
        types.Part.from_bytes(
            data=base64.b64decode(payload.grid_image_b64),
            mime_type='image/jpeg'
        ),
        "What is your next execution plan?"
    ]

    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=GeminiDecision, # ⬅️ Forcing exact alignment with action.py 
                temperature=0.0
            ),
        )
        
        # Hydrate JSON string into the Pydantic Object natively
        decision: GeminiDecision = GeminiDecision.model_validate_json(response.text)

        # Update the Text Ledger Memory!
        human_readable_actions =[f"{act.action.upper()} at {act.target} {'val:' + act.value if act.value else ''}" for act in decision.actions]
        session["ledger"].append(f"Predicted intention based on context: {decision.reasoning}. Fired actions: {human_readable_actions}")

        # Kick the image storage and audit processing to a background CPU thread to not throttle OS cursor.
        bg_tasks.add_task(upload_audit_trail_gcs, payload.session_id, len(session["ledger"]), payload.grid_image_b64, decision)

        return decision

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Use ngrok when deploying locally initially. Map this endpoint URL into `CLOUD_ENDPOINT`.
    uvicorn.run(app, host="0.0.0.0", port=8000)