# Fintel AWS Infrastructure

This Terraform stack describes the production-style learning deployment for Fintel:

- ECS Fargate API service
- ECS Fargate worker service
- Application Load Balancer
- ECR repository
- RDS PostgreSQL
- ElastiCache Redis
- S3 raw filing bucket
- CloudWatch log groups
- Secrets Manager references

It is intentionally a learning/deployment blueprint. Review costs before applying it.

## Usage

```powershell
terraform init
terraform plan `
  -var "project_name=fintel" `
  -var "container_image=ACCOUNT.dkr.ecr.REGION.amazonaws.com/fintel:latest" `
  -var "database_password=..." `
  -var "jwt_secret_key=..." `
  -var "sec_user_agent=Fintel contact@example.com"
```

## Notes

- `database_password`, `jwt_secret_key`, and `openai_api_key` are sensitive variables and are exposed to ECS through Secrets Manager.
- The API and worker use the same image but different commands.
- Redis is used for queue coordination; PostgreSQL stores durable ingestion job state.
- Raw SEC filings are stored in S3 through `DOCUMENT_STORAGE_PROVIDER=s3`.
