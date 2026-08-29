# Fintel Frontend

React/Vite Document Copilot UI for the Fintel FastAPI backend. The app combines chat history, company setup, filing ingestion, and cited filing Q&A in one local interface.

## Local Development

```powershell
npm install
npm run dev
```

The UI expects the API at `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`.

## Checks

```powershell
npm run build
npm run lint
npm run test:e2e
```

The e2e smoke test expects the Docker Compose stack to be running.
