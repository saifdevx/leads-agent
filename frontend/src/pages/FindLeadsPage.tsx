import { useEffect, useMemo, useRef, useState } from 'react'
import { Icon } from '../components/Icon'
import {
  ApiRequestError,
  createSearchPlan,
  getJob,
  getProviders,
  importLeadText,
  startAutomatedSearch,
  type ImportResult,
  type JobStatus,
  type ProviderConnection,
  type SearchPlan,
} from '../lib/api'

type Props = {
  getToken: () => Promise<string>
  onViewLeads: () => void
  onOpenSettings: () => void
}

type Mode = 'automatic' | 'manual'

export function FindLeadsPage({ getToken, onViewLeads, onOpenSettings }: Props) {
  const [niche, setNiche] = useState('Solar panel installers')
  const [location, setLocation] = useState('Texas, USA')
  const [targetCount, setTargetCount] = useState(100)
  const [mode, setMode] = useState<Mode>('automatic')
  const [advanced, setAdvanced] = useState(false)
  const [searchProvider, setSearchProvider] = useState<'auto' | 'serper' | 'brave'>('auto')
  const [aiProvider, setAiProvider] = useState<'auto' | 'none' | 'gemini' | 'openai'>('auto')
  const [crawlWebsites, setCrawlWebsites] = useState(true)
  const [providers, setProviders] = useState<ProviderConnection[]>([])
  const [job, setJob] = useState<JobStatus | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const pollTimer = useRef<number | null>(null)

  const [plan, setPlan] = useState<SearchPlan | null>(null)
  const [selectedQuery, setSelectedQuery] = useState('')
  const [rawText, setRawText] = useState('')
  const [manualResult, setManualResult] = useState<ImportResult | null>(null)

  const [busy, setBusy] = useState<'search' | 'plan' | 'import' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pollWarning, setPollWarning] = useState<string | null>(null)

  async function refreshProviders() {
    try {
      const token = await getToken()
      setProviders(await getProviders(token))
    } catch {
      // The search action will surface a useful error if providers cannot be loaded.
    }
  }

  useEffect(() => { void refreshProviders() }, [])

  useEffect(() => {
    if (!jobId) return
    let cancelled = false

    async function poll() {
      try {
        const token = await getToken()
        const next = await getJob(token, jobId as string)
        if (cancelled) return
        setPollWarning(null)
        setJob(next)
        if (next.status === 'complete' || next.status === 'failed') {
          setBusy(null)
          return
        }
        pollTimer.current = window.setTimeout(() => void poll(), 4000)
      } catch (nextError) {
        if (cancelled) return
        if (nextError instanceof ApiRequestError && nextError.status === 503) {
          setPollWarning('Temporary connection hiccup — the search is still running. Retrying automatically…')
          pollTimer.current = window.setTimeout(() => void poll(), 5000)
          return
        }
        setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not read search progress.')
        setBusy(null)
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (pollTimer.current) window.clearTimeout(pollTimer.current)
    }
  }, [jobId, getToken])

  const connectedSearch = useMemo(() => providers.filter((item) => item.category === 'search' && item.connected), [providers])
  const connectedAi = useMemo(() => providers.filter((item) => item.category === 'ai' && item.connected), [providers])
  const automaticReady = connectedSearch.length > 0

  async function startSearch() {
    setBusy('search')
    setError(null)
    setPollWarning(null)
    setJob(null)
    try {
      const token = await getToken()
      const next = await startAutomatedSearch(token, {
        niche: niche.trim(),
        location: location.trim() || undefined,
        target_count: targetCount,
        search_provider: searchProvider,
        ai_provider: aiProvider,
        crawl_websites: crawlWebsites,
      })
      setJobId(next.job_id)
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not start automatic lead discovery.')
      setBusy(null)
    }
  }

  async function buildManualPlan() {
    setBusy('plan')
    setError(null)
    setManualResult(null)
    try {
      const token = await getToken()
      const next = await createSearchPlan(token, {
        niche: niche.trim(),
        location: location.trim() || undefined,
        target_count: targetCount,
      })
      setPlan(next)
      setSelectedQuery(next.queries[0] || '')
      setRawText('')
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not create the manual search plan.')
    } finally {
      setBusy(null)
    }
  }

  async function importResults() {
    if (!plan) return
    setBusy('import')
    setError(null)
    try {
      const token = await getToken()
      const next = await importLeadText(token, plan.lead_list.id, {
        raw_text: rawText,
        source_query: selectedQuery || undefined,
      })
      setManualResult(next)
      setRawText('')
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not extract leads from the pasted text.')
    } finally {
      setBusy(null)
    }
  }

  const percent = job?.result.progress_percent ?? 0
  const found = job?.result.found_count ?? 0
  const target = job?.result.target_count ?? targetCount

  return (
    <div className="space-y-5">
      <section className="card-surface rounded-[14px] p-5 sm:p-7 lg:p-8">
        <div className="max-w-[760px]">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#F0EDFF] px-3 py-1.5 text-xs font-bold text-[#6D52EE]">
            <Icon name="spark" className="h-3.5 w-3.5" /> Automated lead discovery
          </div>
          <h2 className="font-display text-[29px] font-bold leading-[1.15] tracking-[-0.035em] text-[#14151C] sm:text-[35px]">Tell us who you want to find.</h2>
          <p className="mt-3 max-w-[680px] text-[15px] leading-7 text-[#555965]">Connected search sources do the research automatically. The app cleans results, checks business websites, removes duplicates and saves useful leads for you.</p>
        </div>

        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Business or niche</span>
            <input className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px]" value={niche} disabled={Boolean(busy)} onChange={(event) => setNiche(event.target.value)} />
          </label>
          <label>
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Location</span>
            <input className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px]" value={location} disabled={Boolean(busy)} onChange={(event) => setLocation(event.target.value)} placeholder="e.g. Texas, USA" />
          </label>
          <label>
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Leads wanted</span>
            <select value={targetCount} disabled={Boolean(busy)} onChange={(event) => setTargetCount(Number(event.target.value))} className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px]">
              {[25, 50, 100, 250, 500].map((count) => <option key={count} value={count}>{count}</option>)}
            </select>
          </label>
        </div>

        <button type="button" onClick={() => setAdvanced((value) => !value)} className="focus-ring mt-5 flex items-center gap-2 rounded-lg px-1 py-2 text-sm font-semibold text-[#5E46CF] hover:text-[#7B61FF]">
          Advanced options <Icon name="chevron" className={`h-4 w-4 transition ${advanced ? 'rotate-90' : ''}`} />
        </button>

        {advanced && (
          <div className="mt-2 grid gap-4 rounded-[12px] border border-[#E5E3EF] bg-[#FAF9FF] p-4 sm:grid-cols-3 sm:p-5">
            <label>
              <span className="mb-2 block text-xs font-bold text-[#51545F]">Search source</span>
              <select value={searchProvider} onChange={(event) => setSearchProvider(event.target.value as typeof searchProvider)} className="focus-ring h-10 w-full rounded-[8px] border border-[#DCDDE5] bg-white px-3 text-sm">
                <option value="auto">Smart / automatic</option>
                <option value="serper">Serper / Google</option>
                <option value="brave">Brave Search</option>
              </select>
            </label>
            <label>
              <span className="mb-2 block text-xs font-bold text-[#51545F]">AI cleanup</span>
              <select value={aiProvider} onChange={(event) => setAiProvider(event.target.value as typeof aiProvider)} className="focus-ring h-10 w-full rounded-[8px] border border-[#DCDDE5] bg-white px-3 text-sm">
                <option value="auto">Automatic</option>
                <option value="none">Off</option>
                <option value="gemini">Gemini</option>
                <option value="openai">OpenAI</option>
              </select>
            </label>
            <label className="flex items-end gap-3 pb-2">
              <input type="checkbox" checked={crawlWebsites} onChange={(event) => setCrawlWebsites(event.target.checked)} className="h-4 w-4 accent-[#7B61FF]" />
              <span className="text-sm font-semibold text-[#51545F]">Check company websites</span>
            </label>
          </div>
        )}

        {error && <div role="alert" className="mt-5 rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>}

        {!automaticReady && mode === 'automatic' && (
          <div className="mt-6 rounded-[12px] border border-[#E2DDF8] bg-[#F8F6FF] p-4 sm:flex sm:items-center sm:justify-between sm:gap-4">
            <div>
              <div className="text-sm font-bold text-[#43358B]">Connect a search provider first</div>
              <p className="mt-1 text-xs leading-5 text-[#706A91]">Serper is the closest match to your Google workflow. Brave can add independent web coverage.</p>
            </div>
            <button type="button" onClick={onOpenSettings} className="focus-ring mt-3 h-9 rounded-[8px] bg-[#7B61FF] px-3.5 text-xs font-bold text-white sm:mt-0">Open Settings</button>
          </div>
        )}

        {job && (
          <div className="mt-6 rounded-[13px] border border-[#E2E0ED] bg-[#FCFBFF] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-sm font-bold text-[#2D3038]">{job.status === 'complete' ? 'Lead search complete' : job.status === 'failed' ? 'Search stopped' : job.result.current_step || 'Finding leads'}</div>
                <div className="mt-1 text-xs text-[#747784]">{found} / {target} leads found{job.result.search_calls ? ` · ${job.result.search_calls} search calls` : ''}{job.result.websites_checked ? ` · ${job.result.websites_checked} websites checked` : ''}</div>
              </div>
              <span className={`rounded-md px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-[0.06em] ${job.status === 'complete' ? 'bg-[#F0F8DC] text-[#668126]' : job.status === 'failed' ? 'bg-[#FFF0EE] text-[#A34840]' : 'bg-[#F0EDFF] text-[#6D52EE]'}`}>{job.status}</span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#E9E7F1]"><div className="h-full rounded-full bg-[#7B61FF] transition-all" style={{ width: `${Math.max(2, Math.min(100, percent))}%` }} /></div>
            {job.result.errors && job.result.errors.length > 0 && <p className="mt-3 text-xs leading-5 text-[#8A6C41]">Some sources had issues, but the search continued where possible.</p>}
            {pollWarning && <p className="mt-3 rounded-[8px] bg-[#FFF8E8] px-3 py-2 text-xs font-medium leading-5 text-[#82631F]">{pollWarning}</p>}
            {job.status === 'complete' && <button type="button" onClick={onViewLeads} className="focus-ring mt-4 inline-flex h-10 items-center gap-2 rounded-[9px] bg-[#7B61FF] px-4 text-sm font-bold text-white">View My Leads <Icon name="arrow" className="h-4 w-4" /></button>}
          </div>
        )}

        {!job && mode === 'automatic' && (
          <div className="mt-7 flex flex-col-reverse gap-3 border-t border-[#ECECF1] pt-6 sm:flex-row sm:items-center sm:justify-between">
            <button type="button" onClick={() => setMode('manual')} className="focus-ring text-left text-xs font-bold text-[#777A87] hover:text-[#5E46CF]">Use manual fallback instead</button>
            <button type="button" disabled={!automaticReady || Boolean(busy) || niche.trim().length < 2} onClick={() => void startSearch()} className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-[10px] bg-[#7B61FF] px-5 text-sm font-bold text-white shadow-sm hover:bg-[#6C52EE] disabled:cursor-not-allowed disabled:opacity-50">
              <Icon name="search" className="h-4 w-4" /> {busy === 'search' ? 'Starting…' : 'Find Leads'}
            </button>
          </div>
        )}
      </section>

      {mode === 'automatic' && !job && (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="card-surface rounded-[12px] p-4"><div className="text-xs font-bold uppercase tracking-[0.07em] text-[#8A8D97]">Search</div><div className="mt-2 text-sm font-bold text-[#31343C]">{connectedSearch.length ? connectedSearch.map((item) => item.label).join(' + ') : 'No source connected'}</div></div>
          <div className="card-surface rounded-[12px] p-4"><div className="text-xs font-bold uppercase tracking-[0.07em] text-[#8A8D97]">AI cleanup</div><div className="mt-2 text-sm font-bold text-[#31343C]">{connectedAi.length ? connectedAi.map((item) => item.label).join(' / ') : 'Optional — deterministic fallback'}</div></div>
          <div className="card-surface rounded-[12px] p-4"><div className="text-xs font-bold uppercase tracking-[0.07em] text-[#8A8D97]">Enrichment</div><div className="mt-2 text-sm font-bold text-[#31343C]">Public websites first</div></div>
        </section>
      )}

      {mode === 'manual' && (
        <section className="card-surface rounded-[14px] p-5 sm:p-7">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="font-display text-xl font-bold text-[#22242B]">Manual fallback</h3>
              <p className="mt-1 text-sm text-[#777A87]">Keep the old copy-and-paste workflow available when you do not want to spend search credits.</p>
            </div>
            <button type="button" onClick={() => { setMode('automatic'); setPlan(null); setManualResult(null) }} className="focus-ring h-9 rounded-[8px] border border-[#DDDDE4] px-3 text-xs font-bold text-[#676A75]">Back to automatic</button>
          </div>

          {!plan ? (
            <button type="button" disabled={Boolean(busy)} onClick={() => void buildManualPlan()} className="focus-ring mt-5 h-10 rounded-[9px] bg-[#7B61FF] px-4 text-sm font-bold text-white">Generate manual queries</button>
          ) : (
            <div className="mt-5 grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
              <div className="space-y-2">
                {plan.queries.map((query) => (
                  <button key={query} type="button" onClick={() => setSelectedQuery(query)} className={`focus-ring w-full rounded-[8px] border p-3 text-left text-xs leading-5 ${selectedQuery === query ? 'border-[#A793FF] bg-[#F5F2FF] text-[#4D3BA3]' : 'border-[#E2E2E8] bg-white text-[#636670]'}`}>{query}</button>
                ))}
              </div>
              <div>
                <textarea value={rawText} onChange={(event) => setRawText(event.target.value)} placeholder="Paste visible search results here…" className="focus-ring min-h-[260px] w-full resize-y rounded-[10px] border border-[#DCDDE5] p-4 text-sm leading-6" />
                <div className="mt-3 flex items-center justify-between gap-3">
                  {manualResult ? <span className="text-xs font-bold text-[#668126]">Added {manualResult.added_count} · {manualResult.duplicate_count} duplicates</span> : <span />}
                  <button type="button" disabled={!rawText.trim() || Boolean(busy)} onClick={() => void importResults()} className="focus-ring h-10 rounded-[9px] bg-[#7B61FF] px-4 text-sm font-bold text-white disabled:opacity-50">Extract & save</button>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
