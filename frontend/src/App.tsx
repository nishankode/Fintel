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
  PanelLeft,
  Pencil,
  Play,
  Plus,
  RefreshCcw,
  Send,
  Settings2,
  SquarePen,
  Trash2,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { clsx } from 'clsx'
import './index.css'
import { ApiError, api, getStoredToken, setStoredToken } from './lib/api'
import type { Company, EvidenceResult, Filing, IngestionJob, RetrievalMode } from './lib/api'

type Notice = {
  kind: 'success' | 'error'
  text: string
} | null

type Confirmation = {
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
} | null

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  evidence?: EvidenceResult[]
}

type SessionConfig = {
  companyId: number | null
  companyTicker: string
  companyName: string
  filingTypes: string[]
  filingYears: number[]
  jobId: number | null
  status: 'draft' | 'queued' | 'running' | 'completed' | 'failed'
}

type ChatSession = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
  config?: SessionConfig
}

const CHAT_STORAGE_KEY = 'fintel_chat_sessions'
const ACTIVE_CHAT_STORAGE_KEY = 'fintel_active_chat_session'

const sampleCompanies = [
  { ticker: 'AAPL', cik: '0000320193', name: 'Apple Inc.' },
  { ticker: 'MSFT', cik: '0000789019', name: 'Microsoft Corporation' },
  { ticker: 'NVDA', cik: '0001045810', name: 'NVIDIA Corporation' },
]

const starterPrompts = [
  'How has Apple revenue mix shifted over the last three fiscal years?',
  'What were the main risks discussed in the latest 10-K?',
  'Summarize liquidity and cash flow trends.',
  'Which business segments are most important?',
]

const filingTypeOptions = ['10-K', '10-Q', '8-K']
const filingYearOptions = Array.from(
  { length: 8 },
  (_, index) => new Date().getFullYear() - index,
)

const welcomeMessage: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: 'Ask a question about your indexed SEC filings. I will answer from retrieved evidence and attach citations below the response.',
}

function App() {
  const queryClient = useQueryClient()
  const [token, setToken] = useState(() => getStoredToken())
  const [notice, setNotice] = useState<Notice>(null)
  const [confirmation, setConfirmation] = useState<Confirmation>(null)
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadSessions())
  const [activeSessionId, setActiveSessionId] = useState(() => loadActiveSessionId())
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const isAuthed = Boolean(token)
  const auth = useMemo(() => ({ token }), [token])
  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? sessions[0]

  useEffect(() => {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(sessions))
  }, [sessions])

  useEffect(() => {
    if (activeSession?.id) {
      localStorage.setItem(ACTIVE_CHAT_STORAGE_KEY, activeSession.id)
    }
  }, [activeSession?.id])

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
  const deleteCompanyMutation = useMutation({
    mutationFn: (company: Company) => api.deleteCompany(company.ticker, { token }),
    onError: showError,
    onSuccess: (_response, company) => {
      handleCompanyDeleted(company)
      setNotice({ kind: 'success', text: `${company.ticker} deleted from your filing corpus.` })
    },
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

  function createSession() {
    const session = makeSession()
    setSessions((current) => [session, ...current])
    setActiveSessionId(session.id)
    setEditingSessionId(session.id)
    setNotice(null)
  }

  function requestDeleteSession(sessionId: string) {
    const session = sessions.find((current) => current.id === sessionId)
    if (!session) return

    setConfirmation({
      title: 'Delete session',
      message: `Delete "${session.title}"? This removes the local chat history for this session.`,
      confirmLabel: 'Delete',
      onConfirm: () => deleteSession(sessionId),
    })
  }

  function deleteSession(sessionId: string) {
    const remainingSessions = sessions.filter((current) => current.id !== sessionId)
    const nextSessions = remainingSessions.length > 0 ? remainingSessions : [makeSession()]
    setSessions(nextSessions)
    if (activeSession.id === sessionId) {
      setActiveSessionId(nextSessions[0].id)
      setEditingSessionId(!nextSessions[0].config ? nextSessions[0].id : null)
    }
    setNotice({ kind: 'success', text: 'Session deleted.' })
  }

  function requestDeleteCompany(company: Company) {
    setConfirmation({
      title: `Delete ${company.ticker}`,
      message: `Delete ${company.name} and all local filings, chunks, embeddings, and ingestion jobs for it?`,
      confirmLabel: 'Delete company',
      onConfirm: () => deleteCompanyMutation.mutate(company),
    })
  }

  function handleCompanyDeleted(company: Company) {
    const remainingSessions = sessions.filter((session) => !isSessionForCompany(session, company))
    const nextSessions = remainingSessions.length > 0 ? remainingSessions : [makeSession()]
    const nextActiveSession = nextSessions.find((session) => session.id === activeSession.id) ?? nextSessions[0]

    setSessions(nextSessions)
    setActiveSessionId(nextActiveSession.id)
    setEditingSessionId(!nextActiveSession.config ? nextActiveSession.id : null)
    refreshCompanies()
    refreshFilings()
  }

  const updateSession = useCallback((sessionId: string, updater: (session: ChatSession) => ChatSession) => {
    setSessions((current) => {
      if (!current.some((session) => session.id === sessionId)) return current

      return current
        .map((session) => session.id === sessionId ? updater(session) : session)
        .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
    })
  }, [])

  const updateActiveSession = useCallback((updater: (session: ChatSession) => ChatSession) => {
    updateSession(activeSession.id, updater)
  }, [activeSession.id, updateSession])

  const updateSetupSession = useCallback((updater: (session: ChatSession) => ChatSession) => {
    updateSession(activeSession.id, updater)
  }, [activeSession.id, updateSession])

  const refreshCompanies = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['companies', token] })
  }, [queryClient, token])

  const refreshFilings = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['filings', token] })
  }, [queryClient, token])

  function editSession(sessionId: string) {
    setActiveSessionId(sessionId)
    setEditingSessionId(sessionId)
    setNotice(null)
  }

  function finishEditingSession() {
    setEditingSessionId(null)
    queryClient.invalidateQueries({ queryKey: ['filings', token] })
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
          ready={healthQuery.data?.status === 'ready'}
          sessions={sessions}
          activeSessionId={activeSession.id}
          onNewSession={createSession}
          onSelectSession={(sessionId) => {
            setActiveSessionId(sessionId)
            setEditingSessionId(null)
          }}
          onEditSession={editSession}
          onDeleteSession={requestDeleteSession}
          onRefresh={() => queryClient.invalidateQueries()}
          onSignOut={() => handleToken(null)}
        />
        {shouldConfigureSession(activeSession, editingSessionId) ? (
          <SessionSetup
            token={token}
            ready={healthQuery.data?.status === 'ready'}
            session={activeSession}
            companies={companiesQuery.data ?? []}
            filings={filingsQuery.data ?? []}
            companiesLoading={companiesQuery.isLoading}
            filingsLoading={filingsQuery.isLoading}
            notice={notice}
            onDismissNotice={() => setNotice(null)}
            onError={showError}
            onUpdateSession={updateSetupSession}
            onCompaniesChanged={refreshCompanies}
            onFilingsChanged={refreshFilings}
            onComplete={finishEditingSession}
            onSuccess={(text) => setNotice({ kind: 'success', text })}
            onDeleteCompany={requestDeleteCompany}
          />
        ) : (
          <ChatWorkspace
            token={token}
            session={activeSession}
            notice={notice}
            onDismissNotice={() => setNotice(null)}
            onError={showError}
            onUpdateSession={updateActiveSession}
          />
        )}
        <ConfirmDialog
          confirmation={confirmation}
          onCancel={() => setConfirmation(null)}
          onConfirm={() => {
            confirmation?.onConfirm()
            setConfirmation(null)
          }}
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
          <div><p className="eyebrow">SEC filing assistant</p><h1>Document Copilot</h1></div>
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

function ConfirmDialog({
  confirmation,
  onCancel,
  onConfirm,
}: {
  confirmation: Confirmation
  onCancel: () => void
  onConfirm: () => void
}) {
  if (!confirmation) return null

  return (
    <div className="confirm-backdrop" role="presentation" onClick={onCancel}>
      <section
        aria-labelledby="confirm-title"
        aria-modal="true"
        className="confirm-dialog"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="confirm-mark">
          <Trash2 size={18} aria-hidden="true" />
        </div>
        <div className="confirm-copy">
          <h2 id="confirm-title">{confirmation.title}</h2>
          <p>{confirmation.message}</p>
        </div>
        <div className="confirm-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>Cancel</button>
          <button className="danger-button" type="button" onClick={onConfirm}>{confirmation.confirmLabel}</button>
        </div>
      </section>
    </div>
  )
}

function Sidebar({
  ready,
  sessions,
  activeSessionId,
  onNewSession,
  onSelectSession,
  onEditSession,
  onDeleteSession,
  onRefresh,
  onSignOut,
}: {
  ready: boolean
  sessions: ChatSession[]
  activeSessionId: string
  onNewSession: () => void
  onSelectSession: (id: string) => void
  onEditSession: (id: string) => void
  onDeleteSession: (id: string) => void
  onRefresh: () => void
  onSignOut: () => void
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <div className="brand-mark dark"><FileSearch size={18} aria-hidden="true" /></div>
          <div><h1>Document Copilot</h1><p>SEC filing assistant</p></div>
        </div>
        <button className="new-session-button" type="button" onClick={onNewSession}>
          <SquarePen size={16} aria-hidden="true" />
          New session
        </button>
        <nav className="session-list" aria-label="Chat history">
          <p>Today</p>
          {sessions.map((session) => (
            <div
              className={clsx('session-row', session.id === activeSessionId && 'active')}
              key={session.id}
              title={session.title}
            >
              <button
                className="session-button"
                type="button"
                onClick={() => onSelectSession(session.id)}
              >
                <span>{session.title}</span>
                {session.config && (
                  <small>{session.config.companyTicker} - {session.config.filingTypes.join(', ')}</small>
                )}
              </button>
              <button
                className="session-edit-button"
                type="button"
                title="Edit session"
                onClick={(event) => {
                  event.stopPropagation()
                  onEditSession(session.id)
                }}
              >
                <Pencil size={14} aria-hidden="true" />
              </button>
              <button
                className="session-delete-button"
                type="button"
                title="Delete session"
                onClick={(event) => {
                  event.stopPropagation()
                  onDeleteSession(session.id)
                }}
              >
                <Trash2 size={14} aria-hidden="true" />
              </button>
            </div>
          ))}
        </nav>
      </div>
      <div className="sidebar-bottom">
        <div className="sidebar-actions">
          <StatusPill label={ready ? 'Ready' : 'Checking'} healthy={ready} />
          <button className="icon-button" type="button" title="Refresh workspace" onClick={onRefresh}><RefreshCcw size={17} aria-hidden="true" /></button>
        </div>
        <button className="account-button" type="button" onClick={onSignOut}>
          <span>DA</span>
          <span><strong>analyst@example.com</strong><small>Signed in</small></span>
          <LogOut size={15} aria-hidden="true" />
        </button>
      </div>
    </aside>
  )
}

function SessionSetup({
  token,
  ready,
  session,
  companies,
  filings,
  companiesLoading,
  filingsLoading,
  notice,
  onDismissNotice,
  onError,
  onUpdateSession,
  onCompaniesChanged,
  onFilingsChanged,
  onComplete,
  onSuccess,
  onDeleteCompany,
}: {
  token: string | null
  ready: boolean
  session: ChatSession
  companies: Company[]
  filings: Filing[]
  companiesLoading: boolean
  filingsLoading: boolean
  notice: Notice
  onDismissNotice: () => void
  onError: (error: unknown) => void
  onUpdateSession: (updater: (session: ChatSession) => ChatSession) => void
  onCompaniesChanged: () => void
  onFilingsChanged: () => void
  onComplete: () => void
  onSuccess: (message: string) => void
  onDeleteCompany: (company: Company) => void
}) {
  const selectedCompany = session.config?.companyTicker
    ? companies.find((company) => company.ticker === session.config?.companyTicker)
    : null

  return (
    <section className="session-setup">
      <header className="chat-header">
        <button className="plain-icon" type="button" title="Sidebar"><PanelLeft size={17} aria-hidden="true" /></button>
        <div>
          <p className="eyebrow">Session setup</p>
          <h2>{session.config ? 'Edit session corpus' : 'Configure new session'}</h2>
        </div>
      </header>
      {notice && <button className={clsx('notice', notice.kind)} type="button" onClick={onDismissNotice}>{notice.text}</button>}
      <div className="setup-content">
        <section className="setup-intro">
          <h1>{selectedCompany ? `${selectedCompany.ticker} filing chat` : 'Choose the corpus for this chat session'}</h1>
          <p>
            The session will remember its company, filing types, filing years, ingestion progress, and follow-up chat history.
          </p>
        </section>
        <div className="setup-grid">
          <div className="setup-column">
            <CorpusSummary ready={ready} companies={companies} filings={filings} />
            <CompanySetup
              token={token}
              companies={companies}
              loading={companiesLoading}
              onError={onError}
              onDeleteCompany={onDeleteCompany}
              onSuccess={(message) => {
                onSuccess(message)
                onCompaniesChanged()
              }}
            />
          </div>
          <div className="setup-column">
            <SessionIngestionSetup
              key={session.id}
              token={token}
              session={session}
              companies={companies}
              onError={onError}
              onSuccess={onSuccess}
              onUpdateSession={onUpdateSession}
              onFilingsChanged={onFilingsChanged}
              onComplete={onComplete}
            />
            <FilingList filings={filterFilingsForSession(filings, session.config)} loading={filingsLoading} />
          </div>
        </div>
      </div>
    </section>
  )
}

function CorpusSummary({ ready, companies, filings }: { ready: boolean; companies: Company[]; filings: Filing[] }) {
  const indexed = filings.filter((filing) => filing.status === 'indexed').length
  return (
    <section className="configure-section">
      <SectionTitle icon={<Database size={16} aria-hidden="true" />} title="Corpus" />
      <div className="metric-grid">
        <Metric label="API" value={ready ? 'Ready' : 'Check'} />
        <Metric label="Companies" value={String(companies.length)} />
        <Metric label="Indexed" value={String(indexed)} />
      </div>
    </section>
  )
}

function CompanySetup({
  token,
  companies,
  loading,
  onError,
  onDeleteCompany,
  onSuccess,
}: {
  token: string | null
  companies: Company[]
  loading: boolean
  onError: (error: unknown) => void
  onDeleteCompany: (company: Company) => void
  onSuccess: (message: string) => void
}) {
  const [ticker, setTicker] = useState('AAPL')
  const [cik, setCik] = useState('0000320193')
  const [name, setName] = useState('Apple Inc.')
  const mutation = useMutation({
    mutationFn: () => api.createCompany({ ticker, cik, name }, { token }),
    onError,
    onSuccess: (company) => onSuccess(`${company.ticker} added to your filing corpus.`),
  })

  return (
    <section className="configure-section">
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
        {companies.map((company) => (
          <div className="compact-row company-row" key={company.id}>
            <strong>{company.ticker}</strong>
            <span>{company.name}</span>
            <button
              className="row-icon-button"
              type="button"
              title={`Delete ${company.ticker}`}
              onClick={() => onDeleteCompany(company)}
            >
              <Trash2 size={14} aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}

function SessionIngestionSetup({
  token,
  session,
  companies,
  onError,
  onSuccess,
  onUpdateSession,
  onFilingsChanged,
  onComplete,
}: {
  token: string | null
  session: ChatSession
  companies: Company[]
  onError: (error: unknown) => void
  onSuccess: (message: string) => void
  onUpdateSession: (updater: (session: ChatSession) => ChatSession) => void
  onFilingsChanged: () => void
  onComplete: () => void
}) {
  const config = session.config ?? makeDraftConfig(companies[0])
  const [ticker, setTicker] = useState(config.companyTicker)
  const [selectedFilingTypes, setSelectedFilingTypes] = useState<string[]>(config.filingTypes)
  const [selectedYears, setSelectedYears] = useState<number[]>(config.filingYears)
  const [jobId, setJobId] = useState<number | null>(config.jobId)
  const selectedCompany = companies.find((company) => company.ticker === ticker)

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
    mutationFn: () => api.createIngestionJob(
      ticker,
      {
        filing_types: selectedFilingTypes,
        filing_years: selectedYears,
      },
      { token },
    ),
    onError,
    onSuccess: (job) => {
      setJobId(job.id)
      onUpdateSession((current) => ({
        ...current,
        title: makeSessionConfigTitle(selectedCompany?.name ?? ticker, selectedYears),
        updatedAt: new Date().toISOString(),
        config: {
          companyId: selectedCompany?.id ?? null,
          companyTicker: ticker,
          companyName: selectedCompany?.name ?? ticker,
          filingTypes: selectedFilingTypes,
          filingYears: selectedYears,
          jobId: job.id,
          status: job.status === 'failed' ? 'failed' : job.status === 'completed' ? 'completed' : job.status === 'running' ? 'running' : 'queued',
        },
      }))
      onSuccess(`Ingestion job ${job.id} queued.`)
    },
  })
  const canIngest = Boolean(ticker && selectedFilingTypes.length > 0 && selectedYears.length > 0 && !mutation.isPending)
  const job = jobQuery.data ?? null
  const canChat = session.config?.status === 'completed' || job?.status === 'completed'

  useEffect(() => {
    if (!job) return

    onUpdateSession((current) => {
      const nextStatus = job.status === 'failed' ? 'failed' : job.status === 'completed' ? 'completed' : job.status === 'running' ? 'running' : 'queued'
      if (current.config?.jobId !== job.id || current.config.status === nextStatus) return current
      return {
        ...current,
        updatedAt: new Date().toISOString(),
        config: {
          ...current.config,
          status: nextStatus,
        },
      }
    })

    if (job.status === 'completed') {
      onFilingsChanged()
    }
  }, [job, job?.status, onFilingsChanged, onUpdateSession])

  return (
    <section className="configure-section">
      <SectionTitle icon={<Play size={16} aria-hidden="true" />} title="Session corpus" />
      <div className="stacked-form">
        <label>Company<select value={ticker} onChange={(event) => setTicker(event.target.value)}><option value="">Select company</option>{companies.map((company) => <option value={company.ticker} key={company.id}>{company.ticker} - {company.name}</option>)}</select></label>
        <CheckboxGroup
          label="Filing types"
          options={filingTypeOptions}
          selected={selectedFilingTypes}
          onToggle={(filingType) => setSelectedFilingTypes((current) => toggleValue(current, filingType))}
        />
        <YearCheckboxGroup
          label="Filing years"
          options={filingYearOptions}
          selected={selectedYears}
          onToggle={(year) => setSelectedYears((current) => toggleValue(current, year))}
        />
        <button className="primary-button" type="button" disabled={!canIngest} onClick={() => mutation.mutate()}>
          {mutation.isPending ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          Chunk and embed filings
        </button>
        <button className="secondary-button" type="button" disabled={!canChat} onClick={onComplete}>
          <Send size={16} aria-hidden="true" />
          Start chatting
        </button>
      </div>
      <JobStatus job={job} loading={jobQuery.isFetching} />
    </section>
  )
}

function CheckboxGroup({ label, options, selected, onToggle }: { label: string; options: string[]; selected: string[]; onToggle: (value: string) => void }) {
  return (
    <div className="check-group">
      <span>{label}</span>
      <div>
        {options.map((option) => (
          <button className={clsx('check-button', selected.includes(option) && 'selected')} type="button" key={option} onClick={() => onToggle(option)}>
            <CheckCircle2 size={14} aria-hidden="true" />
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}

function YearCheckboxGroup({ label, options, selected, onToggle }: { label: string; options: number[]; selected: number[]; onToggle: (value: number) => void }) {
  return (
    <div className="check-group">
      <span>{label}</span>
      <div>
        {options.map((option) => (
          <button className={clsx('check-button', selected.includes(option) && 'selected')} type="button" key={option} onClick={() => onToggle(option)}>
            <CheckCircle2 size={14} aria-hidden="true" />
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}

function FilingList({ filings, loading }: { filings: Filing[]; loading: boolean }) {
  return (
    <section className="configure-section">
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

function ChatWorkspace({
  token,
  session,
  notice,
  onDismissNotice,
  onError,
  onUpdateSession,
}: {
  token: string | null
  session: ChatSession
  notice: Notice
  onDismissNotice: () => void
  onError: (error: unknown) => void
  onUpdateSession: (updater: (session: ChatSession) => ChatSession) => void
}) {
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<RetrievalMode>('hybrid')
  const filters = session.config
    ? {
        ticker: session.config.companyTicker,
        filing_types: session.config.filingTypes,
        filing_years: session.config.filingYears,
      }
    : undefined
  const messages = session.messages.length > 0 ? session.messages : [welcomeMessage]
  const mutation = useMutation({
    mutationFn: ({ apiQuestion }: { apiQuestion: string }) =>
      api.askQuestion({ question: apiQuestion, top_k: 5, retrieval_mode: mode, filters }, { token }),
    onError,
    onSuccess: (answer) => {
      onUpdateSession((current) => ({
        ...current,
        updatedAt: new Date().toISOString(),
        messages: [
          ...current.messages,
          { id: `assistant-${Date.now()}`, role: 'assistant', content: answer.answer, evidence: answer.evidence },
        ],
      }))
    },
  })

  function ask(prompt: string) {
    const trimmed = prompt.trim()
    if (!trimmed || mutation.isPending) return

    const priorMessages = session.messages.filter((message) => message.id !== 'welcome')
    const apiQuestion = buildContextualQuestion(trimmed, priorMessages)
    const now = new Date().toISOString()

    onDismissNotice()
    onUpdateSession((current) => ({
      ...current,
      title: current.title === 'New session' ? makeTitle(trimmed) : current.title,
      updatedAt: now,
      messages: [
        ...current.messages.filter((message) => message.id !== 'welcome'),
        { id: `user-${Date.now()}`, role: 'user', content: trimmed },
      ],
    }))
    setQuestion('')
    mutation.mutate({ apiQuestion })
  }

  return (
    <section className="chat-workspace">
      <header className="chat-header">
        <button className="plain-icon" type="button" title="Sidebar"><PanelLeft size={17} aria-hidden="true" /></button>
        <h2>{session.title}</h2>
        <div className="chat-settings">
          <div className="segmented-control small" aria-label="Retrieval mode">
            <button className={clsx(mode === 'semantic' && 'active')} type="button" onClick={() => setMode('semantic')}>Semantic</button>
            <button className={clsx(mode === 'hybrid' && 'active')} type="button" onClick={() => setMode('hybrid')}>Hybrid</button>
          </div>
          {session.config && <div className="inline-select readonly">
            <Settings2 size={15} aria-hidden="true" />
            <span>{session.config.companyTicker} - {session.config.filingTypes.join(', ')} - {session.config.filingYears.join(', ')}</span>
          </div>}
        </div>
      </header>
      {notice && <div className={clsx('notice', notice.kind)}>{notice.text}</div>}
      {session.messages.length === 0 && (
        <div className="prompt-strip">
          {starterPrompts.map((prompt) => <button className="prompt-chip" type="button" key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}
        </div>
      )}
      <div className="message-list" aria-live="polite">
        {messages.map((message) => <ChatBubble message={message} key={message.id} />)}
        {mutation.isPending && (
          <div className="message-row assistant">
            <div className="avatar"><Bot size={16} aria-hidden="true" /></div>
            <div className="message-card thinking"><Loader2 className="spin" size={16} aria-hidden="true" /> Retrieving evidence...</div>
          </div>
        )}
      </div>
      <form className="composer-wrap" onSubmit={(event) => { event.preventDefault(); ask(question) }}>
        <div className="composer">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                ask(question)
              }
            }}
            placeholder="Ask about SEC filings..."
            rows={2}
          />
          <button className="send-button" type="submit" disabled={!question.trim() || mutation.isPending} title="Send question">
            {mutation.isPending ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
          </button>
        </div>
        <p>Answers are grounded in SEC filings. Verify citations before relying on them.</p>
      </form>
    </section>
  )
}

function ChatBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={clsx('message-row', message.role)}>
      {message.role === 'assistant' && <div className="avatar"><Bot size={16} aria-hidden="true" /></div>}
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
          <summary><span>{index + 1}</span>{item.ticker} · {item.filing_type} · {item.accession_number}</summary>
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

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY)
    if (!raw) return [makeSession()]
    const parsed = JSON.parse(raw) as ChatSession[]
    const sessions = parsed.map((session) => ({
      ...session,
      title: session.title === 'New chat' ? 'New session' : session.title,
      messages: session.messages ?? [],
    }))
    return sessions.length > 0 ? sessions : [makeSession()]
  } catch {
    return [makeSession()]
  }
}

function loadActiveSessionId() {
  return localStorage.getItem(ACTIVE_CHAT_STORAGE_KEY) ?? ''
}

function makeSession(): ChatSession {
  const now = new Date().toISOString()
  return {
    id: `session-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    title: 'New session',
    createdAt: now,
    updatedAt: now,
    messages: [],
  }
}

function makeDraftConfig(company?: Company): SessionConfig {
  return {
    companyId: company?.id ?? null,
    companyTicker: company?.ticker ?? '',
    companyName: company?.name ?? '',
    filingTypes: ['10-K'],
    filingYears: [new Date().getFullYear()],
    jobId: null,
    status: 'draft',
  }
}

function makeSessionConfigTitle(companyName: string, filingYears: number[]) {
  const years = [...filingYears].sort((left, right) => right - left)
  const yearLabel = years.length > 2
    ? `${Math.min(...years)}-${Math.max(...years)}`
    : years.join(', ')

  return `${companyName} ${yearLabel}`.trim()
}

function shouldConfigureSession(session: ChatSession, editingSessionId: string | null) {
  return editingSessionId === session.id || !session.config
}

function filterFilingsForSession(filings: Filing[], config?: SessionConfig) {
  if (!config?.companyTicker) return filings

  return filings.filter((filing) => {
    const filedYear = new Date(filing.filed_at).getFullYear()
    return (
      (config.companyId === null || filing.company_id === config.companyId)
      &&
      config.filingTypes.includes(filing.filing_type)
      && config.filingYears.includes(filedYear)
    )
  })
}

function isSessionForCompany(session: ChatSession, company: Company) {
  return (
    session.config?.companyId === company.id
    || session.config?.companyTicker === company.ticker
  )
}

function makeTitle(prompt: string) {
  return prompt.length > 44 ? `${prompt.slice(0, 41)}...` : prompt
}

function toggleValue<T>(values: T[], value: T) {
  return values.includes(value)
    ? values.filter((current) => current !== value)
    : [...values, value]
}

function buildContextualQuestion(prompt: string, priorMessages: ChatMessage[]) {
  if (priorMessages.length === 0) return prompt

  const context = priorMessages
    .slice(-6)
    .map((message) => `${message.role === 'user' ? 'User' : 'Assistant'}: ${message.content}`)
    .join('\n')

  return `Previous conversation:\n${context}\n\nFollow-up question: ${prompt}`
}

export default App
