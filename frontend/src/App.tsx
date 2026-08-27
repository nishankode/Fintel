import type { FormEvent, ReactNode } from 'react'
import {
  Bot,
  Building2,
  CheckCircle2,
  Database,
  FileSearch,
  Loader2,
  LogIn,
  LogOut,
  Play,
  Plus,
  RefreshCcw,
  Send,
  Settings2,
  User,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { clsx } from 'clsx'
import './index.css'
import { ApiError, api, getStoredToken, setStoredToken } from './lib/api'
import type { Company, EvidenceResult, Filing, IngestionJob, RetrievalMode } from './lib/api'

type Notice = {
  kind: 'success' | 'error'
  text: string
} | null

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  evidence?: EvidenceResult[]
}

const sampleCompanies = [
  { ticker: 'AAPL', cik: '0000320193', name: 'Apple Inc.' },
  { ticker: 'MSFT', cik: '0000789019', name: 'Microsoft Corporation' },
  { ticker: 'NVDA', cik: '0001045810', name: 'NVIDIA Corporation' },
]

const starterPrompts = [
  'What are the main risks discussed in the latest filing?',
  'What drove revenue growth?',
  'Summarize liquidity and cash flow trends.',
  'Which business segments are most important?',
]

function App() {
  const queryClient = useQueryClient()
  const [token, setToken] = useState(() => getStoredToken())
  const [notice, setNotice] = useState<Notice>(null)
  const isAuthed = Boolean(token)
  const auth = useMemo(() => ({ token }), [token])

  const healthQuery = useQuery({
    queryKey: ['readiness'],
    queryFn: api.readiness,
    refetchInterval: 15000,
  })
  const companiesQuery = useQuery({
    queryKey: ['companies', token],
    queryFn: () => api.listCompanies(auth),
    enabled: isAuthed,
  })
  const filingsQuery = useQuery({
    queryKey: ['filings', token],
    queryFn: () => api.listFilings(auth),
    enabled: isAuthed,
  })

  function showError(error: unknown) {
    setNotice({
      kind: 'error',
      text: error instanceof ApiError ? error.message : 'Something went wrong. Check the API logs for details.',
    })
  }

  function handleToken(nextToken: string | null) {
    setStoredToken(nextToken)
    setToken(nextToken)
    setNotice(null)
    queryClient.clear()
  }

  if (!isAuthed) {
    return (
      <main className="app-shell">
        <AuthPanel
          ready={healthQuery.data?.status === 'ready'}
          onAuthenticated={(nextToken) => {
            handleToken(nextToken)
            setNotice({ kind: 'success', text: 'Signed in. Ask questions once your filing corpus is ready.' })
          }}
          onError={showError}
        />
      </main>
    )
  }

  return (
    <main className="app-shell full">
      <div className="chat-app">
        <Sidebar
          token={token}
          ready={healthQuery.data?.status === 'ready'}
          companies={companiesQuery.data ?? []}
          filings={filingsQuery.data ?? []}
          companiesLoading={companiesQuery.isLoading}
          filingsLoading={filingsQuery.isLoading}
          onRefresh={() => queryClient.invalidateQueries()}
          onSignOut={() => handleToken(null)}
          onError={showError}
          onSuccess={(text) => {
            setNotice({ kind: 'success', text })
            queryClient.invalidateQueries({ queryKey: ['companies', token] })
            queryClient.invalidateQueries({ queryKey: ['filings', token] })
          }}
        />
        <ChatWorkspace
          token={token}
          companies={companiesQuery.data ?? []}
          notice={notice}
          onDismissNotice={() => setNotice(null)}
          onError={showError}
        />
      </div>
    </main>
  )
}

function AuthPanel({ ready, onAuthenticated, onError }: { ready: boolean; onAuthenticated: (token: string) => void; onError: (error: unknown) => void }) {
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
  const busy = registerMutation.isPending || loginMutation.isPending

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (mode === 'register') {
      registerMutation.mutate()
      return
    }
    loginMutation.mutate()
  }

  return (
    <section className="auth-layout">
      <div className="auth-copy">
        <div className="brand-lockup">
          <div className="brand-mark"><FileSearch size={22} aria-hidden="true" /></div>
          <div><p className="eyebrow">SEC filings intelligence</p><h1>Fintel</h1></div>
        </div>
        <h2>Chat with filings and inspect every answer through citations.</h2>
        <div className="capability-list">
          <span><CheckCircle2 size={16} aria-hidden="true" /> Async SEC ingestion</span>
          <span><CheckCircle2 size={16} aria-hidden="true" /> Hybrid retrieval</span>
          <span><CheckCircle2 size={16} aria-hidden="true" /> Evidence-backed answers</span>
        </div>
      </div>
      <form className="auth-panel" onSubmit={handleSubmit}>
        <StatusPill label={ready ? 'Ready' : 'Checking'} healthy={ready} />
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

function Sidebar({
  token,
  ready,
  companies,
  filings,
  companiesLoading,
  filingsLoading,
  onRefresh,
  onSignOut,
  onError,
  onSuccess,
}: {
  token: string | null
  ready: boolean
  companies: Company[]
  filings: Filing[]
  companiesLoading: boolean
  filingsLoading: boolean
  onRefresh: () => void
  onSignOut: () => void
  onError: (error: unknown) => void
  onSuccess: (message: string) => void
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark"><FileSearch size={20} aria-hidden="true" /></div>
        <div><p className="eyebrow">Fintel</p><h1>Research Chat</h1></div>
      </div>
      <div className="sidebar-actions">
        <StatusPill label={ready ? 'Ready' : 'Checking'} healthy={ready} />
        <button className="icon-button" type="button" title="Refresh workspace" onClick={onRefresh}><RefreshCcw size={17} aria-hidden="true" /></button>
        <button className="icon-button" type="button" title="Sign out" onClick={onSignOut}><LogOut size={17} aria-hidden="true" /></button>
      </div>
      <CorpusSummary companies={companies} filings={filings} />
      <CompanySetup token={token} companies={companies} loading={companiesLoading} onError={onError} onSuccess={onSuccess} />
      <IngestionSetup token={token} companies={companies} onError={onError} onSuccess={onSuccess} />
      <FilingList filings={filings} loading={filingsLoading} />
    </aside>
  )
}

function CorpusSummary({ companies, filings }: { companies: Company[]; filings: Filing[] }) {
  const indexed = filings.filter((filing) => filing.status === 'indexed').length
  return (
    <section className="sidebar-section">
      <SectionTitle icon={<Database size={16} aria-hidden="true" />} title="Corpus" />
      <div className="metric-grid">
        <Metric label="Companies" value={String(companies.length)} />
        <Metric label="Filings" value={String(filings.length)} />
        <Metric label="Indexed" value={String(indexed)} />
      </div>
    </section>
  )
}

function CompanySetup({ token, companies, loading, onError, onSuccess }: { token: string | null; companies: Company[]; loading: boolean; onError: (error: unknown) => void; onSuccess: (message: string) => void }) {
  const [ticker, setTicker] = useState('AAPL')
  const [cik, setCik] = useState('0000320193')
  const [name, setName] = useState('Apple Inc.')
  const mutation = useMutation({
    mutationFn: () => api.createCompany({ ticker, cik, name }, { token }),
    onError,
    onSuccess: (company) => onSuccess(`${company.ticker} added to your filing corpus.`),
  })

  return (
    <section className="sidebar-section">
      <SectionTitle icon={<Building2 size={16} aria-hidden="true" />} title="Companies" />
      <form className="stacked-form" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <label>Ticker<input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} /></label>
        <label>CIK<input value={cik} onChange={(event) => setCik(event.target.value)} /></label>
        <label>Company name<input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <div className="sample-row">
          {sampleCompanies.map((company) => (
            <button className="chip-button" type="button" key={company.ticker} onClick={() => { setTicker(company.ticker); setCik(company.cik); setName(company.name) }}>{company.ticker}</button>
          ))}
        </div>
        <button className="primary-button" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}
          Add company
        </button>
      </form>
      <div className="compact-list">
        {loading && <EmptyState text="Loading companies..." />}
        {!loading && companies.length === 0 && <EmptyState text="No companies yet." />}
        {companies.slice(0, 6).map((company) => (
          <div className="compact-row" key={company.id}><strong>{company.ticker}</strong><span>{company.name}</span></div>
        ))}
      </div>
    </section>
  )
}

function IngestionSetup({ token, companies, onError, onSuccess }: { token: string | null; companies: Company[]; onError: (error: unknown) => void; onSuccess: (message: string) => void }) {
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
    <section className="sidebar-section">
      <SectionTitle icon={<Play size={16} aria-hidden="true" />} title="Ingestion" />
      <div className="stacked-form">
        <label>Company<select value={ticker} onChange={(event) => setTicker(event.target.value)}><option value="">Select company</option>{companies.map((company) => <option value={company.ticker} key={company.id}>{company.ticker} - {company.name}</option>)}</select></label>
        <div className="two-col">
          <label>Filing<select value={filingType} onChange={(event) => setFilingType(event.target.value)}><option>10-K</option><option>10-Q</option><option>8-K</option></select></label>
          <label>Limit<input type="number" min="1" max="10" value={limit} onChange={(event) => setLimit(Number(event.target.value))} /></label>
        </div>
        <button className="primary-button" type="button" disabled={!ticker || mutation.isPending} onClick={() => mutation.mutate()}>
          {mutation.isPending ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          Ingest filings
        </button>
      </div>
      <JobStatus job={jobQuery.data ?? null} loading={jobQuery.isFetching} />
    </section>
  )
}

function FilingList({ filings, loading }: { filings: Filing[]; loading: boolean }) {
  return (
    <section className="sidebar-section">
      <SectionTitle icon={<FileSearch size={16} aria-hidden="true" />} title="Recent filings" />
      <div className="compact-list">
        {loading && <EmptyState text="Loading filings..." />}
        {!loading && filings.length === 0 && <EmptyState text="No filings indexed yet." />}
        {filings.slice(0, 6).map((filing) => (
          <div className="compact-row filing-row" key={filing.id}>
            <strong>{filing.filing_type}</strong>
            <span>{filing.accession_number}</span>
            <StatusPill label={filing.status} healthy={filing.status === 'indexed'} />
          </div>
        ))}
      </div>
    </section>
  )
}

function ChatWorkspace({ token, companies, notice, onDismissNotice, onError }: { token: string | null; companies: Company[]; notice: Notice; onDismissNotice: () => void; onError: (error: unknown) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Ask a question about your indexed SEC filings. I will answer from retrieved evidence and attach citations below the response.',
    },
  ])
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<RetrievalMode>('hybrid')
  const [ticker, setTicker] = useState('')
  const mutation = useMutation({
    mutationFn: (prompt: string) => api.askQuestion({ question: prompt, top_k: 5, retrieval_mode: mode, filters: ticker ? { ticker } : undefined }, { token }),
    onError,
    onSuccess: (answer) => {
      setMessages((current) => [
        ...current,
        { id: `assistant-${Date.now()}`, role: 'assistant', content: answer.answer, evidence: answer.evidence },
      ])
    },
  })

  function ask(prompt: string) {
    const trimmed = prompt.trim()
    if (!trimmed || mutation.isPending) return
    onDismissNotice()
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: 'user', content: trimmed }])
    setQuestion('')
    mutation.mutate(trimmed)
  }

  return (
    <section className="chat-workspace">
      <header className="chat-header">
        <div><p className="eyebrow">Evidence chat</p><h2>Ask filings questions</h2></div>
        <div className="chat-settings">
          <div className="segmented-control small" aria-label="Retrieval mode">
            <button className={clsx(mode === 'semantic' && 'active')} type="button" onClick={() => setMode('semantic')}>Semantic</button>
            <button className={clsx(mode === 'hybrid' && 'active')} type="button" onClick={() => setMode('hybrid')}>Hybrid</button>
          </div>
          <label className="inline-select">
            <Settings2 size={15} aria-hidden="true" />
            <select value={ticker} onChange={(event) => setTicker(event.target.value)}>
              <option value="">All companies</option>
              {companies.map((company) => <option value={company.ticker} key={company.id}>{company.ticker}</option>)}
            </select>
          </label>
        </div>
      </header>
      {notice && <div className={clsx('notice', notice.kind)}>{notice.text}</div>}
      <div className="prompt-strip">
        {starterPrompts.map((prompt) => <button className="prompt-chip" type="button" key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}
      </div>
      <div className="message-list" aria-live="polite">
        {messages.map((message) => <ChatBubble message={message} key={message.id} />)}
        {mutation.isPending && (
          <div className="message-row assistant">
            <div className="avatar"><Bot size={16} aria-hidden="true" /></div>
            <div className="message-card thinking"><Loader2 className="spin" size={16} aria-hidden="true" /> Retrieving evidence...</div>
          </div>
        )}
      </div>
      <form className="composer" onSubmit={(event) => { event.preventDefault(); ask(question) }}>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about risks, revenue, liquidity, segments, guidance, or management discussion..." rows={2} />
        <button className="send-button" type="submit" disabled={!question.trim() || mutation.isPending} title="Send question">
          {mutation.isPending ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
        </button>
      </form>
    </section>
  )
}

function ChatBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={clsx('message-row', message.role)}>
      <div className="avatar">{message.role === 'assistant' ? <Bot size={16} aria-hidden="true" /> : <User size={16} aria-hidden="true" />}</div>
      <div className="message-card">
        <p>{message.content}</p>
        {message.evidence && message.evidence.length > 0 && <CitationList evidence={message.evidence} />}
      </div>
    </div>
  )
}

function CitationList({ evidence }: { evidence: EvidenceResult[] }) {
  return (
    <div className="citation-list">
      {evidence.map((item, index) => (
        <details className="citation-card" key={`${item.chunk_id}-${index}`}>
          <summary><span>[{index + 1}] {item.ticker} {item.filing_type}</span><span>{item.section_key}</span></summary>
          <p>{item.text}</p>
        </details>
      ))}
    </div>
  )
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return <div className="section-title">{icon}<h2>{title}</h2></div>
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>
}

function JobStatus({ job, loading }: { job: IngestionJob | null; loading: boolean }) {
  if (!job) return <EmptyState text="Queue a job to watch ingestion state." />
  const progress = Math.max(0, Math.min(100, job.progress_percent ?? 0))

  return (
    <div className="job-status">
      <div className="job-status-header">
        <div>
          <span>Job #{job.id}</span>
          <strong>{job.status}</strong>
        </div>
        <div className="job-progress-percent">
          {loading && <Loader2 className="spin" size={15} aria-hidden="true" />}
          <strong>{progress}%</strong>
        </div>
      </div>
      <div className="progress-track" aria-label={`Ingestion progress ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="job-progress-meta">
        <span>{job.progress_message ?? 'Waiting for worker update'}</span>
        <span>{job.progress_current}/{job.progress_total || 1}</span>
      </div>
      {job.error_message && <p>{job.error_message}</p>}
    </div>
  )
}

function StatusPill({ label, healthy }: { label: string; healthy: boolean }) {
  return <span className={clsx('status-pill', healthy && 'healthy')}>{label}</span>
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>
}

export default App
