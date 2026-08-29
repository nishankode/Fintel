# API Walkthrough

This walkthrough is the practical story of the application: create a user, register a company, ingest filings, wait for indexing, retrieve evidence, and ask grounded questions.

## 1. Start Services

For local Docker:

```powershell
docker compose up --build
docker compose run --rm api alembic upgrade head
```

For local Python, run PostgreSQL and Redis first, then:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

Check health:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

The local Document Copilot UI runs at:

```text
http://localhost:5173
```

The repeatable UI smoke test lives in `frontend/tests/ui-smoke.spec.ts` and can be run after the local stack is up:

```powershell
cd frontend
npm run test:e2e
```

The UI keeps chat sessions in the left sidebar. A new session opens a corpus setup screen where you choose the company, one or more filing types, and one or more filing years. The ingestion job chunks and embeds matching SEC filings, shows percentage progress, and then unlocks the cited chat screen. Follow-up questions stay inside the same configured session.

## 2. Create A User

```powershell
curl -X POST http://localhost:8000/auth/register `
  -H "Content-Type: application/json" `
  -d "{\"email\":\"analyst@example.com\",\"password\":\"ChangeMe123!\"}"
```

The password is hashed with Argon2 before storage. The raw password never belongs in the database.

## 3. Log In

```powershell
curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=analyst@example.com&password=ChangeMe123!"
```

Copy the returned `access_token` into a shell variable:

```powershell
$token = "paste-token-here"
```

Authenticated routes use:

```powershell
-H "Authorization: Bearer $token"
```

## 4. Create A Company

```powershell
curl -X POST http://localhost:8000/companies `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"ticker\":\"AAPL\",\"cik\":\"0000320193\",\"name\":\"Apple Inc.\"}"
```

Companies are the local starting point for ingestion. The SEC integration discovers filings from the CIK/ticker metadata.

To remove a company and its related local filings, chunks, embeddings, and ingestion jobs:

```powershell
curl -X DELETE http://localhost:8000/companies/AAPL `
  -H "Authorization: Bearer $token"
```

## 5. Queue Filing Ingestion

```powershell
curl -X POST http://localhost:8000/ingestion/companies/AAPL/jobs `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"filing_types\":[\"10-K\",\"10-Q\"],\"filing_years\":[2024,2025]}"
```

This creates an `ingestion_jobs` row and pushes the job ID to Redis. The worker performs the slow work outside the API request.

Embedding throughput is controlled by `EMBEDDING_BATCH_SIZE` and `EMBEDDING_CPU_THREADS`. The default batch size is `128`; on a local CPU-only machine, try `EMBEDDING_CPU_THREADS=4` or `8` if ingestion is still too slow.

## 6. Poll Job Status

```powershell
curl http://localhost:8000/ingestion/jobs/1 `
  -H "Authorization: Bearer $token"
```

Expected status movement:

```text
queued -> running -> completed
```

If something fails, the job is marked `failed` in PostgreSQL with error details. Redis is only a queue signal, not the source of truth.

## 7. Retrieve Evidence

Semantic retrieval:

```powershell
curl -X POST http://localhost:8000/retrieval/semantic `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"What drove revenue growth?\",\"top_k\":5,\"filters\":{\"ticker\":\"AAPL\",\"filing_type\":\"10-K\"}}"
```

Hybrid retrieval:

```powershell
curl -X POST http://localhost:8000/retrieval/hybrid `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"What drove revenue growth?\",\"top_k\":5,\"filters\":{\"ticker\":\"AAPL\",\"filing_type\":\"10-K\"}}"
```

Semantic retrieval is vector similarity. Hybrid retrieval fuses vector search with PostgreSQL full-text search.

## 8. Ask A Grounded Question

```powershell
curl -X POST http://localhost:8000/query `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"What were the main risks discussed in the latest 10-K?\",\"top_k\":5,\"retrieval_mode\":\"hybrid\",\"filters\":{\"ticker\":\"AAPL\",\"filing_type\":\"10-K\"}}"
```

The response contains:

- `answer`: synthesized from retrieved evidence.
- `evidence`: cited chunks with filing, company, section, and chunk metadata.

With `LLM_PROVIDER=extractive`, answers are deterministic local summaries. With `LLM_PROVIDER=openai`, the backend sends only the evidence context and question to the OpenAI Responses API.

## 9. What To Explain In An Interview

- The API keeps routes thin and puts behavior in services.
- PostgreSQL is the durable source of truth for users, filings, chunks, embeddings, and jobs.
- pgvector enables semantic retrieval over filing chunks.
- Redis only decouples API requests from long-running ingestion work.
- Raw SEC filings live in local disk or S3, not in PostgreSQL.
- RAG responses are citation-first: the answer is useful only because the evidence comes back with it.
- The release gate is automated with unit tests, Alembic checks, Compose config validation, Terraform validation, and a real Compose smoke test.
