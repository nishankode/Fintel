output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "api_url" {
  value = "http://${aws_lb.api.dns_name}"
}

output "filings_bucket" {
  value = aws_s3_bucket.filings.bucket
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}
