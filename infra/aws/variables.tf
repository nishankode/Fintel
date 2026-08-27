variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "fintel"
}

variable "container_image" {
  type        = string
  description = "Full image URI for the API and worker containers."
}

variable "app_version" {
  type    = string
  default = "0.1.0"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "database_name" {
  type    = string
  default = "fintel"
}

variable "database_username" {
  type    = string
  default = "fintel"
}

variable "database_password" {
  type      = string
  sensitive = true
}

variable "jwt_secret_key" {
  type      = string
  sensitive = true
}

variable "sec_user_agent" {
  type        = string
  description = "SEC-compliant User-Agent with contact info."
}

variable "openai_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "llm_provider" {
  type    = string
  default = "extractive"
}

variable "openai_model" {
  type    = string
  default = "gpt-5-mini"
}

variable "desired_api_count" {
  type    = number
  default = 1
}

variable "desired_worker_count" {
  type    = number
  default = 1
}
