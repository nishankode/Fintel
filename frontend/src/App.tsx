import type { FormEvent, ReactNode } from 'react'
import {
  Activity,
  Building2,
  CheckCircle2,
  Database,
  FileSearch,
  Loader2,
  LogIn,
  LogOut,
  Play,
  RefreshCcw,
  Search,
  Send,
  Shield,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { clsx } from 'clsx'
import './index.css'
import { ApiError, api, getStoredToken, setStoredToken } from './lib/api'
import type { Company, Filing, IngestionJob, QueryResponse, RetrievalMode, SearchResponse } from './lib/api'

type Notice = {
  kind: 'success' | 'error'
  text: string
} | null

const sampleCompanies = [
  { ticker: 'AAPL', cik: '0000320193', name: 'Apple Inc.' },
  { ticker: 'MSFT', cik: '0000789019', name: 'Microsoft Corporation' },
  { ticker: 'NVDA', cik: '0001045810', name: 'NVIDIA Corporation' },
]

function App() {
  const queryClient = useQueryClient()
  const [token, setToken] = useState(() => getStoredToken())
  const [notice, setNotice] = useState<Notice>(null)
  const isAuthed = Boolean(token)

  const authHeaders = useMemo(() => ({ token }), [token])
  const healthQuery = useQuery({
    queryKey: ['readiness'],
    queryFn: api.readiness,
    refetchInterval: 15000,
  })
  const companiesQuery = useQuery({
    queryKey: ['companies', token],
    queryFn: () => api.listCompanies(authHeaders),
    enabled: isAuthed,
  })
  const filingsQuery = useQuery({
    queryKey: ['filings', token],
    queryFn: () => api.listFilings(authHeaders),
    enabled: isAuthed,
  })

  function handleToken(nextToken: string | null) {
    setStoredToken(nextToken)
    setToken(nextToken)
    setNotice(null)
    queryClient.clear()
  }

  function showError(error: unknown) {
    setNotice({
      kind: 'error',
      text: error instanceof ApiError ? error.message : 'Something went wrong. Check the API logs for details.',
    })
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <FileSearch size={21} aria-hidden="true" />
          </div>
          <div>
            <p className="eyebrow">SEC filings intelligence</p>
            <h1>Fintel Analyst Console</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <StatusPill label={healthQuery.data?.status ?? 'checking'} healthy={healthQuery.data?.status === 'ready'} />
          {isAuthed && (
            <button className="icon-button" type="button" onClick={() => handleToken(null)} title="Sign out">
              <LogOut size={18} aria-hidden="true" />
            </button>
          )}
        </div>
      </header>

      {notice && (
        <div className={clsx('notice', notice.kind)} role="status">
          {notice.text}
        </div>
      )}

      {!isAuthed ? (
        <AuthPanel
          onAuthenticated={(nextToken) => {
            handleToken(nextToken)
            setNotice({ kind: 'success', text: 'Signed in. You can now add companies and query filings.' })
          }}
          onError={showError}
        />
      ) : (
        <div className="workspace-grid">
          <section className="panel span-4">
            <PanelHeader
              icon={<Shield size={18} aria-hidden="true" />}
              title="Session"
              action={
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    queryClient.invalidateQueries()
                    setNotice({ kind: 'success', text: 'Workspace refreshed.' })
                  }}
                >
                  <RefreshCcw size={15} aria-hidden="true" />
                  Refresh
                </button>
              }
            />
            <MetricGrid
              companies={companiesQuery.data ?? []}
              filings={filingsQuery.data ?? []}
              ready={healthQuery.data?.status === 'ready'}
            />
          </section>

          <section className="panel span-8">
            <PanelHeader icon={<Building2 size={18} aria-hidden="true" />} title="Companies" />
            <CompanyManager
              token={token}
              companies={companiesQuery.data ?? []}
              loading={companiesQuery.isLoading}
              onError={showError}
              onSuccess={(text) => {
                setNotice({ kind: 'success', text })
                queryClient.invalidateQueries({ queryKey: ['companies', token] })
              }}
            />
          </section>

          <section className="panel span-5">
            <PanelHeader icon={<Play size={18} aria-hidden="true" />} title="Ingestion" />
            <IngestionDesk token={token} companies={companiesQuery.data ?? []} onError={showError} onSuccess={(text) => setNotice({ kind: 'success', text })} />
          </section>

          <section className="panel span-7">
            <PanelHeader icon={<Database size={18} aria-hidden="true" />} title="Filings" />
            <FilingTable filings={filingsQuery.data ?? []} loading={filingsQuery.isLoading} />
          </section>

          <section className="panel span-6">
            <PanelHeader icon={<Search size={18} aria-hidden="true" />} title="Evidence Search" />
            <RetrievalDesk token={token} companies={companiesQuery.data ?? []} onError={showError} />
          </section>

          <section className="panel span-6">
            <PanelHeader icon={<Send size={18} aria-hidden="true" />} title="Grounded Q&A" />
            <QuestionDesk token={token} companies={companiesQuery.data ?? []} onError={showError} />
          </section>
        </div>
      )}
    </main>
  )
}

function AuthPanel({ onAuthenticated, onError }: { onAuthenticated: (token: string) => void; onError: (error: unknown) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('analyst')
  const [email, setEmail] = useState('analyst@example.com')
  const [password, setPassword] = useState('ChangeMe123!')

  const registerMutation = useMutation({
    mutationFn: () => api.register({ username, email, password }),
    onError,
    onSuccess: () => setMode('login'),
  })
  const loginMutation = useMutation({
    mutationFn: () => api.login({ username, password }),
    onError,
    onSuccess: (response) => onAuthenticated(response.access_token),
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (mode === 'register') {
      registerMutation.mutate()
      return
    }
    loginMutation.mutate()
  }

  const busy = registerMutation.isPending || loginMutation.isPending

  return (
    <section className="auth-layout">
      <div className="auth-copy">
        <p className="eyebrow">Local portfolio demo</p>
        <h2>Search SEC filings like an analyst, with every answer tied back to evidence.</h2>
        <div className="capability-list">
          <span><CheckCircle2 size={16} aria-hidden="true" /> Async SEC ingestion</span>
          <span><CheckCircle2 size={16} aria-hidden="true" /> Semantic and hybrid retrieval</span>
          <span><CheckCircle2 size={16} aria-hidden="true" /> Cited RAG answers</span>
        </div>
      </div>
      <form className="auth-panel" onSubmit={handleSubmit}>
        <div className="segmented-control" aria-label="Authentication mode">
          <button className={clsx(mode === 'login' && 'active')} type="button" onClick={() => setMode('login')}>Login</button>
          <button className={clsx(mode === 'register' && 'active')} type="button" onClick={() => setMode('register')}>Register</button>
        </div>
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} /></label>
        {mode === 'register' && <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>}
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <button className="primary-button" type="submit" disabled={busy}>
          {busy ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <LogIn size={16} aria-hidden="true" />}
          {mode === 'login' ? 'Sign in' : 'Create user'}
        </button>
      </form>
    </section>
  )
}

function CompanyManager({ token, companies, loading, onError, onSuccess }: { token: string | null; companies: Company[]; loading: boolean; onError: (error: unknown) => void; onSuccess: (message: string) => void }) {
  const [ticker, setTicker] = useState('AAPL')
  const [cik, setCik] = useState('0000320193')
  const [name, setName] = useState('Apple Inc.')
  const mutation = useMutation({
    mutationFn: () => api.createCompany({ ticker, cik, name }, { token }),
    onError,
    onSuccess: (company) => onSuccess(`${company.ticker} added to the research universe.`),
  })

  return (
    <div className="split-panel">
      <form className="form-grid" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <label>Ticker<input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} /></label>
        <label>CIK<input value={cik} onChange={(event) => setCik(event.target.value)} /></label>
        <label className="wide">Company name<input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <div className="sample-row wide">
          {sampleCompanies.map((company) => (
            <button className="chip-button" type="button" key={company.ticker} onClick={() => { setTicker(company.ticker); setCik(company.cik); setName(company.name) }}>
              {company.ticker}
            </button>
          ))}
        </div>
        <button className="primary-button wide" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Building2 size={16} aria-hidden="true" />}
          Add company
        </button>
      </form>
      <div className="list-surface">
        {loading && <EmptyState text="Loading companies..." />}
        {!loading && companies.length === 0 && <EmptyState text="No companies yet." />}
        {companies.map((company) => (
          <div className="company-row" key={company.id}>
            <strong>{company.ticker}</strong><span>{company.name}</span><code>{company.cik}</code>
          </div>
        ))}
      </div>
    </div>
  )
}

function IngestionDesk({ token, companies, onError, onSuccess }: { token: string | null; companies: Company[]; onError: (error: unknown) => void; onSuccess: (message: string) => void }) {
  const [ticker, setTicker] = useState('')
  const [filingType, setFilingType] = useState('10-K')
  const [limit, setLimit] = useState(1)
  const [jobId, setJobId] = useState<number | null>(null)
  const jobQuery = useQuery({
    queryKey: ['job', token, jobId],
    queryFn: () => api.getIngestionJob(jobId!, { token }),
    enabled: Boolean(token && jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? 2500 : false
    },
  })
  const mutation = useMutation({
    mutationFn: () => api.createIngestionJob(ticker, { filing_types: [filingType], limit }, { token }),
    onError,
    onSuccess: (job) => { setJobId(job.id); onSuccess(`Ingestion job ${job.id} queued.`) },
  })

  return (
    <div className="vertical-stack">
      <div className="form-grid compact">
        <label>Company<select value={ticker} onChange={(event) => setTicker(event.target.value)}><option value="">Select company</option>{companies.map((company) => <option value={company.ticker} key={company.id}>{company.ticker} - {company.name}</option>)}</select></label>
        <label>Filing<select value={filingType} onChange={(event) => setFilingType(event.target.value)}><option>10-K</option><option>10-Q</option><option>8-K</option></select></label>
        <label>Limit<input type="number" min="1" max="10" value={limit} onChange={(event) => setLimit(Number(event.target.value))} /></label>
        <button className="primary-button" type="button" disabled={!ticker || mutation.isPending} onClick={() => mutation.mutate()}>
          {mutation.isPending ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />} Queue
        </button>
      </div>
      <JobStatus job={jobQuery.data ?? null} loading={jobQuery.isFetching} />
    </div>
  )
}

function RetrievalDesk({ token, companies, onError }: { token: string | null; companies: Company[]; onError: (error: unknown) => void }) {
  const [query, setQuery] = useState('What drove revenue growth?')
  const [mode, setMode] = useState<RetrievalMode>('hybrid')
  const [ticker, setTicker] = useState('')
  const [results, setResults] = useState<SearchResponse | null>(null)
  const mutation = useMutation({
    mutationFn: () => api.searchEvidence(mode, { query, top_k: 5, filters: ticker ? { ticker } : undefined }, { token }),
    onError,
    onSuccess: setResults,
  })

  return (
    <div className="vertical-stack">
      <SearchControls query={query} setQuery={setQuery} mode={mode} setMode={setMode} ticker={ticker} setTicker={setTicker} companies={companies} disabled={mutation.isPending} onRun={() => mutation.mutate()} buttonLabel="Search evidence" />
      <EvidenceList results={results?.results ?? []} loading={mutation.isPending} />
    </div>
  )
}

function QuestionDesk({ token, companies, onError }: { token: string | null; companies: Company[]; onError: (error: unknown) => void }) {
  const [question, setQuestion] = useState('What are the main risks discussed in the filing?')
  const [mode, setMode] = useState<RetrievalMode>('hybrid')
  const [ticker, setTicker] = useState('')
  const [answer, setAnswer] = useState<QueryResponse | null>(null)
  const mutation = useMutation({
    mutationFn: () => api.askQuestion({ question, top_k: 5, retrieval_mode: mode, filters: ticker ? { ticker } : undefined }, { token }),
    onError,
    onSuccess: setAnswer,
  })

  return (
    <div className="vertical-stack">
      <SearchControls query={question} setQuery={setQuestion} mode={mode} setMode={setMode} ticker={ticker} setTicker={setTicker} companies={companies} disabled={mutation.isPending} onRun={() => mutation.mutate()} buttonLabel="Ask" />
      {mutation.isPending && <EmptyState text="Retrieving evidence and composing an answer..." />}
      {answer && <div className="answer-surface"><p>{answer.answer}</p><EvidenceList results={answer.evidence} loading={false} compact /></div>}
      {!answer && !mutation.isPending && <EmptyState text="Ask a question after at least one filing is indexed." />}
    </div>
  )
}

function SearchControls({ query, setQuery, mode, setMode, ticker, setTicker, companies, disabled, onRun, buttonLabel }: { query: string; setQuery: (query: string) => void; mode: RetrievalMode; setMode: (mode: RetrievalMode) => void; ticker: string; setTicker: (ticker: string) => void; companies: Company[]; disabled: boolean; onRun: () => void; buttonLabel: string }) {
  return (
    <div className="search-controls">
      <textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={3} />
      <div className="control-row">
        <div className="segmented-control small" aria-label="Retrieval mode">
          <button className={clsx(mode === 'semantic' && 'active')} type="button" onClick={() => setMode('semantic')}>Semantic</button>
          <button className={clsx(mode === 'hybrid' && 'active')} type="button" onClick={() => setMode('hybrid')}>Hybrid</button>
        </div>
        <select value={ticker} onChange={(event) => setTicker(event.target.value)}>
          <option value="">All companies</option>
          {companies.map((company) => <option value={company.ticker} key={company.id}>{company.ticker}</option>)}
        </select>
        <button className="primary-button" type="button" disabled={disabled || !query.trim()} onClick={onRun}>
          {disabled ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
          {buttonLabel}
        </button>
      </div>
    </div>
  )
}

function FilingTable({ filings, loading }: { filings: Filing[]; loading: boolean }) {
  if (loading) return <EmptyState text="Loading filings..." />
  if (filings.length === 0) return <EmptyState text="No filings indexed yet." />
  return (
    <div className="table-surface">
      <div className="table-header"><span>Accession</span><span>Type</span><span>Date</span><span>Status</span></div>
      {filings.slice(0, 8).map((filing) => (
        <div className="table-row" key={filing.id}>
          <span title={filing.accession_number}>{filing.accession_number}</span><strong>{filing.filing_type}</strong><span>{filing.filed_at}</span><StatusPill label={filing.status} healthy={filing.status === 'indexed'} />
        </div>
      ))}
    </div>
  )
}

function EvidenceList({ results, loading, compact = false }: { results: Array<SearchResponse['results'][number] | QueryResponse['evidence'][number]>; loading: boolean; compact?: boolean }) {
  if (loading) return <EmptyState text="Searching evidence..." />
  if (results.length === 0) return <EmptyState text="No evidence returned yet." />
  return (
    <div className={clsx('evidence-list', compact && 'compact')}>
      {results.map((result, index) => (
        <article className="evidence-card" key={`${result.chunk_id}-${index}`}>
          <div className="evidence-meta">
            <strong>{result.ticker}</strong><span>{result.filing_type}</span><span>{result.section_key}</span>
            {'cosine_similarity' in result && result.cosine_similarity !== null && result.cosine_similarity !== undefined && <span>{Math.round(result.cosine_similarity * 100)}% match</span>}
            {'rrf_score' in result && result.rrf_score !== undefined && <span>RRF {result.rrf_score.toFixed(4)}</span>}
          </div>
          <p>{result.text}</p>
        </article>
      ))}
    </div>
  )
}

function MetricGrid({ companies, filings, ready }: { companies: Company[]; filings: Filing[]; ready: boolean }) {
  const indexed = filings.filter((filing) => filing.status === 'indexed').length
  return (
    <div className="metric-grid">
      <Metric icon={<Activity size={16} aria-hidden="true" />} label="API" value={ready ? 'Ready' : 'Checking'} />
      <Metric icon={<Building2 size={16} aria-hidden="true" />} label="Companies" value={String(companies.length)} />
      <Metric icon={<Database size={16} aria-hidden="true" />} label="Indexed" value={String(indexed)} />
    </div>
  )
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="metric">{icon}<span>{label}</span><strong>{value}</strong></div>
}

function JobStatus({ job, loading }: { job: IngestionJob | null; loading: boolean }) {
  if (!job) return <EmptyState text="Queue a job to watch ingestion state." />
  return <div className="job-status"><div><span>Job #{job.id}</span><strong>{job.status}</strong></div>{loading && <Loader2 className="spin" size={18} aria-hidden="true" />}{job.error_message && <p>{job.error_message}</p>}</div>
}

function PanelHeader({ icon, title, action }: { icon: ReactNode; title: string; action?: ReactNode }) {
  return <div className="panel-header"><div>{icon}<h2>{title}</h2></div>{action}</div>
}

function StatusPill({ label, healthy }: { label: string; healthy: boolean }) {
  return <span className={clsx('status-pill', healthy && 'healthy')}>{label}</span>
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>
}

export default App
