import { useMemo, useState } from 'react'
import { Icon } from '../components/Icon'
import { ApiRequestError, createSearchPlan, importLeadText, type ImportResult, type SearchPlan } from '../lib/api'

type Props = {
  getToken: () => Promise<string>
  onViewLeads: () => void
}

export function FindLeadsPage({ getToken, onViewLeads }: Props) {
  const [niche, setNiche] = useState('Solar panel installers')
  const [location, setLocation] = useState('Texas, USA')
  const [targetCount, setTargetCount] = useState(100)
  const [advanced, setAdvanced] = useState(false)
  const [plan, setPlan] = useState<SearchPlan | null>(null)
  const [selectedQuery, setSelectedQuery] = useState('')
  const [rawText, setRawText] = useState('')
  const [result, setResult] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState<'plan' | 'import' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copiedQuery, setCopiedQuery] = useState<string | null>(null)

  const canPlan = niche.trim().length >= 2 && !busy
  const canImport = Boolean(plan && rawText.trim().length >= 3 && !busy)
  const progressLabel = useMemo(() => {
    if (!plan) return '1. Describe your target'
    if (!result) return '2. Run a free search and paste results'
    return '3. Leads saved'
  }, [plan, result])

  async function buildPlan() {
    setBusy('plan')
    setError(null)
    setResult(null)
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
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not create the search plan.')
    } finally {
      setBusy(null)
    }
  }

  async function copyQuery(query: string) {
    try {
      await navigator.clipboard.writeText(query)
      setCopiedQuery(query)
      window.setTimeout(() => setCopiedQuery((current) => current === query ? null : current), 1600)
    } catch {
      setError('Could not copy the query. Select the text and copy it manually.')
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
      setResult(next)
      setRawText('')
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not extract leads from the pasted text.')
    } finally {
      setBusy(null)
    }
  }

  function resetSearch() {
    setPlan(null)
    setResult(null)
    setRawText('')
    setSelectedQuery('')
    setError(null)
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="card-surface rounded-[14px] p-5 sm:p-7 lg:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-[700px]">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#F0EDFF] px-3 py-1.5 text-xs font-bold text-[#6D52EE]">
              <Icon name="spark" className="h-3.5 w-3.5" />
              Free lead finder
            </div>
            <h2 className="font-display text-[28px] font-bold leading-[1.15] tracking-[-0.035em] text-[#14151C] sm:text-[34px]">
              Find useful leads without paid databases.
            </h2>
            <p className="mt-3 max-w-[640px] text-[15px] leading-7 text-[#4B4F5E]">
              Build targeted search queries, run them in Google, then paste the visible results here. We extract contact details, remove duplicates and save the leads for you.
            </p>
          </div>
          <div className="shrink-0 rounded-[9px] border border-[#E2E0ED] bg-[#FAF9FF] px-3 py-2 text-xs font-bold text-[#6955C8]">{progressLabel}</div>
        </div>

        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Business or niche</span>
            <input
              className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px] text-[#14151C] placeholder:text-[#9598A4] disabled:bg-[#F5F5F7]"
              placeholder="e.g. Solar panel installers"
              value={niche}
              disabled={Boolean(plan)}
              onChange={(event) => setNiche(event.target.value)}
            />
          </label>

          <label>
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Location</span>
            <input
              className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px] text-[#14151C] placeholder:text-[#9598A4] disabled:bg-[#F5F5F7]"
              placeholder="e.g. Texas, USA"
              value={location}
              disabled={Boolean(plan)}
              onChange={(event) => setLocation(event.target.value)}
            />
          </label>

          <label>
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Target leads</span>
            <select
              value={targetCount}
              disabled={Boolean(plan)}
              onChange={(event) => setTargetCount(Number(event.target.value))}
              className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px] text-[#14151C] disabled:bg-[#F5F5F7]"
            >
              {[25, 50, 100, 250, 500].map((count) => <option key={count} value={count}>{count}</option>)}
            </select>
          </label>
        </div>

        {!plan && (
          <>
            <button
              type="button"
              onClick={() => setAdvanced((value) => !value)}
              className="focus-ring mt-5 flex items-center gap-2 rounded-lg px-1 py-2 text-sm font-semibold text-[#5E46CF] hover:text-[#7B61FF]"
            >
              How free mode works
              <Icon name="chevron" className={`h-4 w-4 transition ${advanced ? 'rotate-90' : ''}`} />
            </button>
            {advanced && (
              <div className="mt-2 rounded-[12px] border border-[#E5E3EF] bg-[#FAF9FF] p-4 text-sm leading-6 text-[#565966] sm:p-5">
                We generate focused searches such as <strong className="font-semibold text-[#292B33]">site:instagram.com &quot;solar installer&quot; &quot;gmail.com&quot;</strong>. You run the searches normally, copy the visible result text, and paste it back here. No paid API is required.
              </div>
            )}
          </>
        )}

        {error && (
          <div role="alert" className="mt-5 rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>
        )}

        {!plan ? (
          <div className="mt-7 flex justify-end border-t border-[#ECECF1] pt-6">
            <button
              type="button"
              disabled={!canPlan}
              onClick={() => void buildPlan()}
              className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-[10px] bg-[#7B61FF] px-5 text-sm font-bold text-white shadow-[0_8px_20px_rgba(123,97,255,0.22)] transition hover:bg-[#6E53F0] disabled:cursor-not-allowed disabled:opacity-55"
            >
              {busy === 'plan' ? 'Creating searches…' : 'Create free search plan'}
              <Icon name="arrow" className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="mt-8 space-y-7 border-t border-[#ECECF1] pt-7">
            <div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="font-display text-lg font-bold tracking-[-0.02em] text-[#1C1E25]">Free searches</h3>
                  <p className="mt-1 text-sm text-[#747784]">Open a query, copy useful result text, then paste it below.</p>
                </div>
                <button type="button" onClick={resetSearch} className="focus-ring rounded-lg px-3 py-2 text-xs font-bold text-[#6A6D78] hover:bg-[#F5F5F8]">Start over</button>
              </div>

              <div className="mt-4 divide-y divide-[#ECECF1] overflow-hidden rounded-[12px] border border-[#E4E4EA] bg-white">
                {plan.queries.map((query, index) => (
                  <div key={query} className="flex flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center">
                    <div className="flex min-w-0 flex-1 items-start gap-3">
                      <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-[#F0EDFF] text-[10px] font-extrabold text-[#6D52EE]">{index + 1}</span>
                      <code className="min-w-0 break-words text-[12px] leading-5 text-[#3D404A]">{query}</code>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button type="button" onClick={() => void copyQuery(query)} className="focus-ring inline-flex h-8 items-center gap-1.5 rounded-[8px] border border-[#E0E0E7] px-2.5 text-xs font-bold text-[#565966] hover:bg-[#F8F8FA]">
                        <Icon name="copy" className="h-3.5 w-3.5" /> {copiedQuery === query ? 'Copied' : 'Copy'}
                      </button>
                      <a href={`https://www.google.com/search?q=${encodeURIComponent(query)}`} target="_blank" rel="noreferrer" className="focus-ring inline-flex h-8 items-center gap-1.5 rounded-[8px] bg-[#14151C] px-2.5 text-xs font-bold text-white hover:bg-[#292A32]">
                        Google <Icon name="external" className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_260px] sm:items-end">
                <div>
                  <label htmlFor="raw-results" className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Paste search result text</label>
                  <p className="mb-3 text-xs leading-5 text-[#7A7D89]">Copy the visible page text or selected search results. Do not paste passwords or private account data.</p>
                </div>
                <label>
                  <span className="mb-2 block text-[12px] font-bold uppercase tracking-[0.07em] text-[#6A6D7B]">Source query</span>
                  <select value={selectedQuery} onChange={(event) => setSelectedQuery(event.target.value)} className="focus-ring h-10 w-full rounded-[9px] border border-[#DCDDE5] bg-white px-3 text-xs text-[#363841]">
                    {plan.queries.map((query, index) => <option key={query} value={query}>Search {index + 1}</option>)}
                  </select>
                </label>
              </div>
              <textarea
                id="raw-results"
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
                placeholder={'Example:\nSun Peak Solar\nhttps://sunpeaksolar.com\nhello@sunpeaksolar.com\n+1 555 123 4567'}
                className="focus-ring min-h-[220px] w-full resize-y rounded-[12px] border border-[#DCDDE5] bg-white p-4 font-mono text-[12px] leading-6 text-[#30323A] placeholder:text-[#A0A2AC]"
              />
              <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-xs text-[#7C7F8A]">{rawText.length.toLocaleString()} characters pasted</div>
                <button
                  type="button"
                  disabled={!canImport}
                  onClick={() => void importResults()}
                  className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-[10px] bg-[#7B61FF] px-5 text-sm font-bold text-white shadow-[0_8px_20px_rgba(123,97,255,0.18)] transition hover:bg-[#6E53F0] disabled:cursor-not-allowed disabled:opacity-55"
                >
                  <Icon name="import" className="h-4 w-4" />
                  {busy === 'import' ? 'Extracting leads…' : 'Extract & save leads'}
                </button>
              </div>
            </div>

            {result && (
              <div className="rounded-[12px] border border-[#DCE8C1] bg-[#FBFFF2] p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-xs font-extrabold uppercase tracking-[0.09em] text-[#607C20]">Import complete</div>
                    <h3 className="mt-1 font-display text-xl font-bold text-[#242A18]">{result.added_count} new lead{result.added_count === 1 ? '' : 's'} saved</h3>
                  </div>
                  <button type="button" onClick={onViewLeads} className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-[9px] bg-[#14151C] px-4 text-sm font-bold text-white hover:bg-[#292A32]">View My Leads <Icon name="arrow" className="h-4 w-4" /></button>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ['Extracted', result.extracted_count],
                    ['Added', result.added_count],
                    ['Duplicates', result.duplicate_count],
                    ['Skipped', result.skipped_count],
                  ].map(([label, value]) => (
                    <div key={String(label)} className="rounded-[9px] border border-[#E1EACA] bg-white/80 px-3 py-2.5">
                      <div className="text-[11px] font-semibold text-[#7C8569]">{label}</div>
                      <div className="mt-0.5 font-display text-lg font-bold text-[#2F381E]">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      <aside className="space-y-4">
        <div className="rounded-[14px] bg-[#14151C] p-5 text-white shadow-[0_12px_28px_rgba(20,21,28,0.12)]">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[#B39CFF]">
            <Icon name="activity" className="h-4 w-4" /> Free workflow
          </div>
          <div className="mt-5 space-y-4">
            {[
              ['Search', 'Use the generated queries in Google'],
              ['Paste', 'Copy visible result text into the app'],
              ['Save', 'We extract and deduplicate contacts'],
            ].map(([title, detail], index) => (
              <div key={title} className="flex items-start gap-3">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white/8 text-xs font-extrabold text-[#C8B9FF]">{index + 1}</div>
                <div><div className="text-sm font-semibold">{title}</div><div className="mt-0.5 text-[11px] leading-5 text-white/50">{detail}</div></div>
              </div>
            ))}
          </div>
        </div>

        <div className="card-surface rounded-[14px] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.1em] text-[#7B61FF]">What gets extracted</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {['Business', 'Email', 'Phone', 'Website', 'LinkedIn', 'Instagram', 'Facebook'].map((item) => (
              <span key={item} className="rounded-md bg-[#F3F2F7] px-2.5 py-1.5 text-[11px] font-semibold text-[#575A65]">{item}</span>
            ))}
          </div>
          <p className="mt-4 text-xs leading-5 text-[#777A87]">Free extraction is best-effort. If a result does not publicly show a contact detail, the app will not invent one.</p>
        </div>
      </aside>
    </div>
  )
}
