# Cloud Run Invoker Service Account
resource "google_service_account" "cloud_run_invoker_sa" {
  account_id   = "cloud-run-invoker"
  display_name = "Cloud Run Invoker"
  provider     = google-beta
  project      = data.google_project.project.project_id
}

# Project IAM binding
resource "google_project_iam_binding" "run_invoker_binding" {
  project = data.google_project.project.project_id
  role    = "roles/run.invoker"
  members = ["serviceAccount:${google_service_account.cloud_run_invoker_sa.email}"]
}

resource "google_project_iam_binding" "token_creator_binding" {
  project = data.google_project.project.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  members = ["serviceAccount:${google_service_account.cloud_run_invoker_sa.email}"]
}

# Cloud Run Job
resource "google_cloud_run_v2_job" "instagram_poster_job" {
  name     = "instagram-poster"
  location = var.region
  project = var.project_id

  template {
    template {

      containers {
        image = "gcr.io/{{ PROJECT_ID }}/instagram-poster"

        env {
          name = "ACCOUNT"
          value = "prod"
        }
        env {
            name = "UPLOAD_TYPE"
            value = "post"
        }
        env {
            name = "HIGHLIGHT"
            value = ""
        }
        env {
            name = "GOOGLE_PROJECT_ID"
            value = var.project_id
        }
      }
      timeout = "900s"
      service_account = "terraform@{{ PROJECT_ID }}.iam.gserviceaccount.com"
      max_retries = 1
    }
    task_count = 1
  }

  lifecycle {
    ignore_changes = [
      launch_stage,
    ]
  }
}

# Cloud Run Job IAM binding
resource "google_cloud_run_v2_job_iam_binding" "binding" {
  project    = data.google_project.project.project_id
  location   = google_cloud_run_v2_job.instagram_poster_job.location
  name       = google_cloud_run_v2_job.instagram_poster_job.name
  role       = "roles/viewer"
  members    = ["serviceAccount:${google_service_account.cloud_run_invoker_sa.email}"]
  depends_on = [google_cloud_run_v2_job.instagram_poster_job]
}


resource "google_cloud_scheduler_job" "instagram_poster_scheduler_job" {
  provider         = google-beta
  name             = "instagram-poster-schedule-job"
  description      = "Runs the Instagram Poster App"
  schedule         = "0 18 2-30/2 * *"
  attempt_deadline = "320s"
  region           = var.region
  project          = var.project_id

  retry_config {
    retry_count = 3
  }

  http_target {
    http_method = "POST"
    uri         = "https://${google_cloud_run_v2_job.instagram_poster_job.location}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${data.google_project.project.number}/jobs/${google_cloud_run_v2_job.instagram_poster_job.name}:run"

    oauth_token {
      service_account_email = google_service_account.cloud_run_invoker_sa.email
    }
  }

}