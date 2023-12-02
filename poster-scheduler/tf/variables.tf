variable "project_id" {
    type    = string
    default = "{{ PROJECT_ID }}"
}

variable "region" {
    type    = string
    default = "europe-west2"
}

data "google_project" "project" {
    project_id = var.project_id
}

output "project_number" {
  value = data.google_project.project.number
}
