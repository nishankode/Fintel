# Deployment Checklist

This project is now deployable as a backend system, but a real deployment still needs environment-specific choices. Use this checklist before spending money on cloud resources.

## Already Implemented

- FastAPI backend with auth, companies, filings, ingestion, retrieval, and query routes.
- PostgreSQL schema migrations through Alembic.
- pgvector-backed semantic retrieval.
- PostgreSQL full-text lexical retrieval.
- Hybrid retrieval with Reciprocal Rank Fusion.
- SEC discovery, raw filing download, parsing, chunking, embedding, and indexing.
- Redis-backed async ingestion jobs with durable job state in PostgreSQL.
- Local and S3-compatible document storage providers.
- Extractive local answer mode and OpenAI Responses API answer mode.
- Request IDs, request logging, exception handlers, readiness checks, and rate limits.
- Docker image, Docker Compose API/worker/Postgres/Redis stack, and Compose smoke test.
- Terraform blueprint for AWS ECS, ALB, RDS, ElastiCache, S3, ECR, Secrets Manager, and CloudWatch.
- GitHub Actions CI for tests, migrations/config validation, and Terraform validation.

## Required Before Deployment

- Replace placeholder secrets:
  - `JWT_SECRET_KEY`
  - database password
  - `SEC_USER_AGENT`
  - optional `OPENAI_API_KEY`
- Decide the deployment target:
  - low-cost VM with Docker Compose
  - AWS ECS Fargate using `infra/aws`
- Decide the answer mode:
  - `LLM_PROVIDER=extractive` for no external LLM cost
  - `LLM_PROVIDER=openai` for generated grounded answers
- Decide the storage provider:
  - local volume for VM deployment
  - S3 for AWS deployment
- Run a cost check for RDS, ElastiCache, ECS, NAT/data transfer, ALB, and storage.
- Confirm SEC user agent contact details are real and compliant with SEC access guidance.
- Point DNS and TLS at the deployed API if exposing it publicly.

## Local Release Gate

Run these before building or deploying:

```powershell
.\.venv\Scripts\python.exe -m compileall app tests
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m alembic current
docker compose config --quiet
cd frontend; npm run build; npm run lint; cd ..
cd frontend; npm run test:e2e; cd ..
terraform -chdir=infra/aws validate
.\scripts\compose-smoke.ps1
```

The frontend e2e smoke test expects the local stack to be running. The Compose smoke script uses the isolated Compose project name `fintel-smoke` by default and removes only that project's volumes after it finishes.

## Docker Compose Deployment Path

Use this path for a cheaper demo deployment on one VM:

1. Install Docker and Docker Compose on the VM.
2. Copy the project or pull it from Git.
3. Create `.env` from `.env.example`.
4. Replace secrets and contact details.
5. Run `docker compose build`.
6. Run `docker compose run --rm api alembic upgrade head`.
7. Run `docker compose up -d`.
8. Check `GET /health` and `GET /health/ready`.
9. Put a reverse proxy with TLS in front of port `8000` before public use.

## AWS Deployment Path

Use this path for the production-style architecture:

1. Create or select an AWS account and region.
2. Review `infra/aws/variables.tf`.
3. Build and push the Docker image to ECR.
4. Run `terraform -chdir=infra/aws init`.
5. Run `terraform -chdir=infra/aws plan` with real variable values.
6. Review cost and networking before applying.
7. Run `terraform -chdir=infra/aws apply`.
8. Run database migrations as a one-off ECS task or through a controlled CI/CD job.
9. Check the ALB health endpoint and ECS service logs.
10. Ingest a small known company and query it end to end.

## Known Production Concerns

- The image includes the local embedding stack and is about 2.16 GB after pinning Linux builds to CPU-only Torch. A later scale optimization could split embedding work into a dedicated service/image.
- The rate limiter is process-local. For multi-instance API traffic, move rate-limit counters to Redis.
- Terraform validates locally, but provider/runtime availability and exact AWS costs still need a real `plan` review in the target account.
- No public frontend is included. The current product surface is an API backend.
