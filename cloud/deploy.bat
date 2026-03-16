@echo off

REM 1. Enable the necessary APIs (skip if already enabled)
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

REM 2. Build the Docker image and push it to Google Container Registry
gcloud builds submit --tag gcr.io/gemini-hackathon-489920/kazi-copilot-brain cloud

REM 3. Deploy the service to Cloud Run
gcloud run deploy kazi-copilot-brain ^
    --image gcr.io/gemini-hackathon-489920/kazi-copilot-brain ^
    --platform managed ^
    --region us-central1 ^
    --allow-unauthenticated ^
    --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest"

echo Deployment complete! Service URL:
gcloud run services describe kazi-copilot-brain --platform managed --region us-central1 --format="value(status.url)"
pause