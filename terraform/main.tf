terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "gemini-hackathon"
  region  = "us-central1" 
}

# Cloud Storage Bucket for the Visual Audit Trail
resource "google_storage_bucket" "audit_trail" {
  name          = "gemini-hackathon-audit-trail"
  location      = "US"
  force_destroy = true 

  uniform_bucket_level_access = true
}

# Google Cloud Run Service (The "Brain")
resource "google_cloud_run_v2_service" "brain_service" {
  name     = "brain-service"
  location = "us-central1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      # Placeholder: Replace with your actual Docker image URL later
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      
      env {
        name  = "BUCKET_NAME"
        value = google_storage_bucket.audit_trail.name
      }
      env {
        name  = "GEMINI_HACKATHON"
        value = "gemini-hackathon"
      }
    }
  }
}