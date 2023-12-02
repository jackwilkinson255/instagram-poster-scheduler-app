resource "google_storage_bucket" "images" {
    name     = "${var.project_id}-images"
    project = var.project_id
    location = var.region
}
