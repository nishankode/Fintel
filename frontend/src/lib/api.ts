const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'fintel_access_token'

export type AuthContext = {
  token: string | null
}

export type Company = {
  id: number
  cik: string
  ticker: string
  name: string
}

export type Filing = {
  id: number
  company_id: number
  accession_number: string
  filing_type: string
  filed_at: string
  reporting_period: string | null
  source_url: string
  status: string
}

export type IngestionJob = {
  id: number
  company_id: number
  job_type: string
  status: string
  payload: Record<string, unknown>
  error_message: string | null
  progress_current: number
  progress_total: number
  progress_percent: number
  progress_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export type RetrievalMode = 'semantic' | 'hybrid'

export type EvidenceResult = {
  chunk_id: number
  filing_id: number
  company_id: number
  ticker: string
  accession_number: string
  filing_type: string
  section_key: string
  chunk_index: number
  text: string
  cosine_distance?: number | null
  cosine_similarity?: number | null
  rrf_score?: number
  semantic_rank?: number | null
  lexical_rank?: number | null
}

export type SearchResponse = {
  query: string
  top_k: number
  results: EvidenceResult[]
}

export type QueryResponse = {
  question: string
  answer: string
  evidence: EvidenceResult[]
}

export type RetrievalFilters = {
  ticker?: string
  filing_type?: string
  filing_types?: string[]
  filing_years?: number[]
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    return
  }

  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

async function request<T>(path: string, options: RequestInit = {}, auth?: AuthContext): Promise<T> {
  const headers = new Headers(options.headers)

  if (auth?.token) {
    headers.set('Authorization', `Bearer ${auth.token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`

    try {
      const body = await response.json()
      message = typeof body.detail === 'string' ? body.detail : message
    } catch {
      // Keep the generic message when the response is not JSON.
    }

    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

function jsonRequest<T>(path: string, body: unknown, auth?: AuthContext) {
  return request<T>(
    path,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    },
    auth,
  )
}

export const api = {
  readiness: () =>
    request<{
      status: string
      dependencies: Array<{ name: string; healthy: boolean; detail: string }>
    }>('/health/ready'),

  register: (body: { username: string; email: string; password: string }) =>
    jsonRequest('/auth/register', body),

  login: (body: { username: string; password: string }) => {
    const form = new URLSearchParams()
    form.set('username', body.username)
    form.set('password', body.password)

    return request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: form,
    })
  },

  listCompanies: (auth: AuthContext) => request<Company[]>('/companies', {}, auth),

  createCompany: (body: { ticker: string; cik: string; name: string }, auth: AuthContext) =>
    jsonRequest<Company>('/companies', body, auth),

  listFilings: (auth: AuthContext) => request<Filing[]>('/filings', {}, auth),

  createIngestionJob: (
    ticker: string,
    body: { filing_types: string[]; filing_years?: number[]; limit?: number },
    auth: AuthContext,
  ) => jsonRequest<IngestionJob>(`/ingestion/companies/${ticker}/jobs`, body, auth),

  getIngestionJob: (jobId: number, auth: AuthContext) =>
    request<IngestionJob>(`/ingestion/jobs/${jobId}`, {}, auth),

  searchEvidence: (
    mode: RetrievalMode,
    body: { query: string; top_k: number; filters?: RetrievalFilters },
    auth: AuthContext,
  ) => jsonRequest<SearchResponse>(`/retrieval/${mode}`, body, auth),

  askQuestion: (
    body: {
      question: string
      top_k: number
      retrieval_mode: RetrievalMode
      filters?: RetrievalFilters
    },
    auth: AuthContext,
  ) => jsonRequest<QueryResponse>('/query', body, auth),
}
