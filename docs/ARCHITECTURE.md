# Fintel Architecture

Fintel is a FastAPI backend for SEC filing intelligence. Its core job is to turn raw EDGAR filings into searchable, cited evidence and then answer questions from that evidence.

## System Map

```text
Client
  -> FastAPI routes
  -> SQLAlchemy services
  -> PostgreSQL + pgvector
  -> Redis ingestion queue
  -> Local disk or S3 document storage
  -> SEC EDGAR APIs
  -> local embedding model
  -> extractive or OpenAI answer synthesis
```

The API and worker share the same code and image. They differ only by command: the API runs Uvicorn, and the worker runs `python -m app.workers.ingestion`.

## Request Lifecycle

1. FastAPI receives the request in `app/main.py`.
2. Middleware adds request IDs, structured request logging, and optional rate limits.
3. Exception handlers convert known failures into consistent HTTP responses.
4. The route resolves configuration from `Settings` and a database session from `DBDependency`.
5. Authenticated routes require `CurrentUserDependency`, which validates a JWT and loads the user.
6. Service classes perform the real work. Routes stay thin and translate service output into response schemas.

## Data Model

PostgreSQL stores durable application state:

- `users`: registered users and hashed passwords.
- `companies`: tracked public companies.
- `filings`: SEC metadata, raw document storage key, and processing status.
- `filing_chunks`: parsed text chunks with section metadata.
- `chunk_embeddings`: pgvector embeddings connected one-to-one with chunks.
- `ingestion_jobs`: durable state for queued ingestion work.

Redis does not store durable truth. It only carries job IDs from the API to the worker.

## Ingestion Flow

```text
POST /ingestion/companies/{ticker}/jobs
  -> verify company exists
  -> create ingestion_jobs row
  -> push job ID onto Redis list
  -> worker pops job ID
  -> discover filings from SEC
  -> upsert filing metadata
  -> download raw HTML
  -> store raw document locally or in S3
  -> parse SEC filing text
  -> split into section-aware chunks
  -> generate embeddings
  -> persist vectors
  -> mark filing indexed
  -> mark job completed or failed
```

The synchronous ingestion endpoint uses the same services without Redis. That is useful for development and debugging, while the queued endpoint is the production path.

## Retrieval Flow

```text
POST /retrieval/semantic
  -> embed the query
  -> search pgvector with cosine distance
  -> apply optional company, filing type, and section filters
  -> return ranked chunks with citation metadata
```

Hybrid retrieval adds PostgreSQL full-text search and combines semantic and lexical ranks with Reciprocal Rank Fusion. RRF is used because semantic similarity and lexical scores are not directly comparable.

## Query Flow

```text
POST /query
  -> retrieve relevant chunks
  -> build a compact evidence context
  -> synthesize an answer
  -> return answer plus citations
```

`LLM_PROVIDER=extractive` keeps local development deterministic and avoids external cost. `LLM_PROVIDER=openai` uses the OpenAI Responses API with the retrieved context.

## Storage Flow

The database stores logical storage keys, not raw filing bodies. This keeps PostgreSQL focused on relational state and search metadata.

- Local development: `DOCUMENT_STORAGE_PROVIDER=local`, files under `data/`.
- Cloud deployment: `DOCUMENT_STORAGE_PROVIDER=s3`, files under the configured bucket and key prefix.

## Reliability Boundaries

- Ingestion status is committed to PostgreSQL at each durable milestone.
- Embedding persistence is idempotent and skips chunks that already have vectors.
- Readiness checks verify database connectivity, Redis connectivity, storage configuration, embedding configuration, and LLM configuration.
- Rate limiting is in-process and appropriate for a single API instance. A distributed limiter would be needed for large multi-instance production traffic.

## Evaluation

The evaluation module has retrieval metrics for Recall@K, reciprocal rank/MRR, and nDCG. These let you compare chunking, embedding models, filters, and hybrid retrieval changes with something better than intuition.
