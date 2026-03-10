# Gemini UI Navigator Project Execution Checklist

## Phase 1: Local Setup & Basic Visual Mechanics (The "Muscle")
- [ ] Set up a new local Python virtual environment (`python -m venv venv`).
- [ ] Install core desktop libraries: `mss`, `pynput`, `Pillow`, `opencv-python`, `SpeechRecognition` (or PyAudio).
- [ ] Write a script using `mss` to capture a full-screen image of the primary monitor and save it locally.
- [ ] Develop the **Set-of-Mark (SoM) Grid Overlay Generator**:
    - Write a Pillow function that divides the monitor's resolution into a 20x20 grid (or similar density).
    - Draw slightly transparent borders for each grid square.
    - Overlay a small, highly contrasted label in each square (A1, A2... Z20).
- [ ] Write the basic OS execution function with `pynput` that accepts a coordinate `(x, y)` and an action type `("click", "double_click", "type")`, moving the mouse and executing the input natively.
-[ ] Map the generated grid labels (e.g., "C4") to physical screen center coordinates so an LLM returning "C4" directly triggers `pynput` at X=200, Y=350.

## Phase 2: GCP & Brain Infrastructure (The Cloud Agent)
- [ ] Set up a Google Cloud Project with a linked Cloud Billing Account.
- [ ] Enable APIs: Cloud Run API, Cloud Storage API, Vertex AI API (or acquire a Google GenAI Studio API key).
- [ ] Write a bare-bones Terraform script (`main.tf`) that creates:
    - A Cloud Storage Bucket (to act as the visual Audit Trail).
    - Provisions a Google Cloud Run Service.
- [ ] Set up the FastAPI python application (The Cloud "Brain"):
    - Define Pydantic models for request payloads (Image + Text Goal) and response structures (`Action`, `Target Grid`, `Typing Text`, `Task Status`).
    - Initialize the GenAI SDK instance (`gemini-1.5-pro`).
- [ ] Engineer the System Instruction prompt: Force the model to only return the JSON format requested, teaching it to search for targets in the image and cross-reference them to the alphanumeric Set-of-Mark grid labels overlay.
- [ ] Connect FastAPI to GCS: Have the server asynchronously dump the incoming grid screenshot and its resulting JSON reasoning into your Cloud Storage bucket, mapping them to a session ID for logging.

## Phase 3: Merging the Brain and Muscle (The Main Loop)
- [ ] Expose your Cloud FastAPI locally using ngrok or `localtunnel` (before full deployment to GCP) for rapid testing.
- [ ] Write the orchestrator loop script locally:
    - Setup system hotkey to begin session.
    - Start Voice-to-Text to acquire user intention.
    - Loop Start: Capture -> Overlay Grid -> Resize/compress if > 4MB to avoid latency -> POST HTTP request -> Parse response JSON.
- [ ] Implement the `diff_check` stability pause before moving to the next cycle loop to account for UI animations.
- [ ] Perform local loop testing on a basic application like "Open notepad, write 'Hello World', click File -> Save." 

## Phase 4: Local/Complex Use-Case Tuning & Failsafes
- [ ] Determine a complex, local Kenyan digital workflow for the demo (e.g., WhatsApp Web -> messy CRM dashboard -> regional Logistics dispatch screen). 
- [ ] Create edge-case system instructions for popups: "If an unexpected ad, GDPR banner, or dialog blocks your target UI, your only valid response in this step is identifying and clicking the close icon."
- [ ] Program a fallback exception state: If Gemini cannot map coordinates with 90%+ confidence, it responds with an action of `{"status": "REQUIRE_HUMAN"}`. The local muscle triggers `say` (mac) or `pyttsx3` (windows) to output audio from speakers asking you to clarify or execute a step manually.
- [ ] Containerize the Brain app using Docker and use `gcloud run deploy` to formally shift your Brain into production on GCP. Update your local daemon pointing from ngrok to the live Cloud Run endpoint URL.

## Phase 5: Hackathon Deliverables (Architecture & Video)
- [ ] Draft a clean, professional Architecture Diagram using LucidChart, Draw.io, or Excalidraw showing the separation between Local OS muscle and GCP-hosted logic/Audit logging. Export as high-res PNG.
- [ ] Produce the screen recording/over-the-shoulder demo. Include hands-free usage where cursor magically hits localized Kenyan dashboards accurately via Cloud AI JSON generation. 
- [ ] Ensure one frame/recording natively pulls up Google Cloud console, viewing the auto-populated GCS storage bucket auditing the "bot decisions." (Required for GCP requirement proof).
- [ ] Finalize code cleanup. Hide API keys. Make README crystal clear. Publish Github repository locally and double check the Spin-up/Installation documentation.
- [ ] Optional Hackathon Strategy: Drop an explicit 40-word mention within the source repo / ReadMe linking to `#GeminiLiveAgentChallenge`. Publish a medium or substack piece to scoop up the remaining bonus points regarding Automating Chrome with Gemini without an API layer. 
- [ ] Draft final DevPost written answers summarizing all files, video uploads, repos. Review submission guidelines thoroughly. Click submit!