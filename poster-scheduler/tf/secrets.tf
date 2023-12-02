# Create a secret for test-account-id
resource "google_secret_manager_secret" "test-account-id" {
  provider = google-beta
  project = var.project_id
  secret_id = ""
  replication {
    automatic = true
  }
}

# Create a secret for prod-account-id
resource "google_secret_manager_secret" "prod-account-id" {
  provider = google-beta
  project = var.project_id
  secret_id = ""
  replication {
    automatic = true
  }
}

# Create a secret for password
resource "google_secret_manager_secret" "password" {
  provider = google-beta
  project = var.project_id
  secret_id = ""
  replication {
    automatic = true
  }
}