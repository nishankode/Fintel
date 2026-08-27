# Fintel

Fintel is a financial intelligence and evidence platform for SEC/EDGAR filings. It ingests public company filings, stores raw source documents, parses and chunks filing text, creates local embeddings, retrieves relevant evidence with pgvector, and exposes a grounded query API.

## Architecture

```text
FastAPI
  -> auth, companies, filings
  -> sync ingestion endpoint
  -> async ingestion job endpoint
  -> semantic retrieval endpoint
  -> grounded query endpoint

PostgreSQL + pgvector
  -> companies, filings, chunks, embeddings, ingestion_jobs

Redis
  -> ingestion job queue only

Local storage
  -> raw downloaded SEC HTML under data/
```

## Ingestion Flow

```text
Company
  -> SEC discovery
  -> filing metadata persistence
  -> raw HTML download
  -> local document storage
  -> SEC-aware parsing
  -> section-aware chunking
  -> local embeddings
  -> chunks.embedding vector(384)
  -> filing.status = indexed
```

The synchronous pipeline is coordinated by `FilingIngestionPipeline` and `CompanyIngestionPipeline`. Individual responsibilities stay separate: SEC access, persistence, storage, parsing, chunking, embedding, and orchestration are different services.

Async ingestion adds `IngestionJob` rows in PostgreSQL and places job IDs onto Redis. PostgreSQL is the durable source of truth; Redis is only the work notification mechanism.

## Query Flow

```text
Question
  -> query embedding
  -> pgvector cosine search
  -> metadata filters
  -> retrieval context
  -> grounded answer service
  -> citations/evidence
```

`SemanticRetriever` performs exact cosine search first. That is intentional while the corpus is small because it is simple, debuggable, and easy to benchmark before introducing ANN indexes.

## Key Design Choices

- Raw SEC HTML is stored outside PostgreSQL; the database stores logical `storage_key` references.
- Chunk embeddings are generated during ingestion, not query time, so retrieval stays low-latency.
- Embedding persistence is idempotent: reruns only process chunks where `embedding IS NULL`.
- A filing is marked `indexed` only after vectors are persisted.
- Redis is not permanent state. Failed/running/completed job state lives in PostgreSQL.
- Retrieval quality has explicit metrics: Recall@K, MRR, and nDCG.

## Local Development

Create a `.env` from `.env.example` and set real values:

```text
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET_KEY=...
SEC_USER_AGENT=Your App your-email@example.com
DEBUG=false
LLM_PROVIDER=extractive
```

Run migrations:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Run tests:

```powershell
$env:DEBUG='false'
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Start the API locally:

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

## Docker Compose

```powershell
docker compose up --build
```

This starts:

- FastAPI API on `localhost:8000`
- ingestion worker
- PostgreSQL with pgvector
- Redis

Apply migrations inside the API container:

```powershell
docker compose run --rm api alembic upgrade head
```

## Important Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /companies`
- `GET /companies`
- `POST /filings`
- `GET /filings`
- `POST /ingestion/companies/{ticker}`
- `POST /ingestion/companies/{ticker}/jobs`
- `GET /ingestion/jobs/{job_id}`
- `POST /retrieval/semantic`
- `POST /query`

## Evaluation

The evaluation layer currently supports retrieval evaluation cases with:

- Recall@K
- reciprocal rank / MRR
- nDCG@K

These metrics are the basis for later decisions about chunk size, overlap, embedding models, lexical search, hybrid retrieval, and reranking.

## LLM Provider

The default query service uses `LLM_PROVIDER=extractive`, which is deterministic and safe for local development. To use OpenAI for grounded answer synthesis, set:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
```

The OpenAI path calls the Responses API from the server and keeps the API key in environment configuration.

## Deployment Direction

The production-style AWS shape is:

```text
ALB
  -> ECS Fargate API
  -> ECS Fargate worker
RDS PostgreSQL + pgvector
ElastiCache Redis
S3 for raw filings
Secrets Manager
CloudWatch
GitHub Actions
```

A cheaper recruiter-facing deployment can run the same API/worker/Postgres/Redis shape on one VM with Docker Compose.
