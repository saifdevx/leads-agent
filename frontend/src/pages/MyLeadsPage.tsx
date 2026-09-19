import { useEffect, useMemo, useState } from 'react'
import { Icon } from '../components/Icon'
import {
  ApiRequestError,
  downloadLeadExport,
  getJob,
  getLeadLists,
  getLeads,
  startLeadEnrichment,
  type Lead,
  type LeadList,
} from '../lib/api'

type Props = { getToken: () => Promise<string> }
type EmailFilter = 'all' | 'verified' | 'has_email' | 'missing_email'
type ExportFormat = 'xlsx' | 'csv'
type EnrichmentProvider = 'auto' | 'prospeo' | 'apollo'

const DEFAULT_TITLES = 'Owner, Founder, CEO, President, Managing Director'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function MyLeadsPage({ getToken }: Props) {
  const [lists, setLists] = useState<LeadList[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [selectedList, setSelectedList] = useState('all')
  const [search, setSearch] = useState('')
  const [emailFilter, setEmailFilter] = useState<EmailFilter>('all')
  const [minScore, setMinScore] = useState('0')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [exportFormat, setExportFormat] = useState<ExportFormat>('xlsx')
  const [exporting, setExporting] = useState(false)
  const [enrichOpen, setEnrichOpen] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichProvider, setEnrichProvider] = useState<EnrichmentProvider>('auto')
  const [targetTitles, setTargetTitles] = useState(DEFAULT_TITLES)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    getToken()
      .then(async (token) => Promise.all([
        getLeadLists(token),
        getLeads(token, selectedList === 'all' ? undefined : selectedList),
      ]))
      .then(([nextLists, nextLeads]) => {
        if (!active) return
        setLists(nextLists)
        setLeads(nextLeads)
        setSelectedIds(new Set())
      })
      .catch((nextError) => {
        if (!active) return
        setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not load your leads.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [getToken, selectedList, refreshKey])

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const minimum = Number(minScore || 0)
    return leads.filter((lead) => {
      if (needle && ![
        lead.company_name, lead.first_name, lead.last_name, lead.job_title, lead.email,
        lead.phone, lead.website, lead.region, lead.domain, lead.source,
      ].some((value) => value?.toLowerCase().includes(needle))) return false
      const email = Boolean(lead.email)
      const verified = email && (lead.email_status || '').toLowerCase() === 'verified'
      if (emailFilter === 'verified' && !verified) return false
      if (emailFilter === 'has_email' && !email) return false
      if (emailFilter === 'missing_email' && email) return false
      if ((lead.score || 0) < minimum) return false
      return true
    })
  }, [leads, search, emailFilter, minScore])

  const filteredIds = useMemo(() => filtered.map((lead) => lead.id), [filtered])
  const allFilteredSelected = filteredIds.length > 0 && filteredIds.every((id) => selectedIds.has(id))
  const selectedCount = selectedIds.size
  const exportCount = selectedCount || filtered.length

  const stats = useMemo(() => {
    const withEmail = filtered.filter((lead) => lead.email).length
    const verified = filtered.filter((lead) => lead.email && (lead.email_status || '').toLowerCase() === 'verified').length
    const highScore = filtered.filter((lead) => (lead.score || 0) >= 85).length
    return { withEmail, verified, highScore }
  }, [filtered])

  function toggleAllFiltered() {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (allFilteredSelected) filteredIds.forEach((id) => next.delete(id))
      else filteredIds.forEach((id) => next.add(id))
      return next
    })
  }

  function toggleLead(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function exportLeads() {
    if (exportCount === 0) return
    setExporting(true)
    setError(null)
    setNotice(null)
    try {
      const token = await getToken()
      const result = await downloadLeadExport(token, {
        format: exportFormat,
        list_id: selectedList === 'all' ? undefined : selectedList,
        lead_ids: selectedCount ? [...selectedIds] : undefined,
        search: selectedCount ? undefined : search.trim() || undefined,
        email_filter: selectedCount ? 'all' : emailFilter,
        min_score: selectedCount ? undefined : Number(minScore || 0) || undefined,
      })
      downloadBlob(result.blob, result.filename)
      setNotice(`Exported ${exportCount} lead${exportCount === 1 ? '' : 's'} to ${exportFormat.toUpperCase()}.`)
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not export leads.')
    } finally {
      setExporting(false)
    }
  }

  async function runEnrichment() {
    if (selectedCount === 0 || selectedCount > 100) return
    setEnriching(true)
    setError(null)
    setNotice(null)
    try {
      const token = await getToken()
      const titles = targetTitles.split(',').map((value) => value.trim()).filter(Boolean).slice(0, 20)
      const start = await startLeadEnrichment(token, {
        lead_ids: [...selectedIds],
        provider: enrichProvider,
        target_titles: titles.length ? titles : DEFAULT_TITLES.split(',').map((value) => value.trim()),
      })
      setEnrichOpen(false)
      let temporaryErrors = 0
      for (;;) {
        await new Promise((resolve) => window.setTimeout(resolve, 4000))
        try {
          const job = await getJob(token, start.job_id)
          temporaryErrors = 0
          if (job.status === 'complete') {
            const enriched = job.result.enriched_count || 0
            const verified = job.result.verified_email_count || 0
            setNotice(`Enrichment finished: ${enriched} updated, ${verified} verified email${verified === 1 ? '' : 's'}.`)
            setSelectedIds(new Set())
            setRefreshKey((value) => value + 1)
            break
          }
          if (job.status === 'failed') {
            throw new ApiRequestError(job.last_error || 'Enrichment failed.', 400)
          }
        } catch (pollError) {
          if (pollError instanceof ApiRequestError && pollError.status === 503 && temporaryErrors < 4) {
            temporaryErrors += 1
            continue
          }
          throw pollError
        }
      }
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not enrich the selected leads.')
    } finally {
      setEnriching(false)
    }
  }

  return (
    <div className="space-y-5">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Visible leads', filtered.length, 'Current filters'],
          ['With email', stats.withEmail, 'Public or enriched'],
          ['Verified email', stats.verified, 'Ready for outreach'],
          ['High fit', stats.highScore, 'Score 85+'],
        ].map(([label, value, helper]) => (
          <div key={String(label)} className="card-surface rounded-[12px] px-5 py-4">
            <div className="text-xs font-bold uppercase tracking-[0.07em] text-[#858894]">{label}</div>
            <div className="mt-1 font-display text-2xl font-bold text-[#1F2128]">{value}</div>
            <div className="mt-1 text-xs text-[#8A8D97]">{helper}</div>
          </div>
        ))}
      </section>

      {notice && <div className="rounded-[10px] border border-[#DDE9B9] bg-[#F7FBEA] px-4 py-3 text-sm font-medium text-[#59731C]">{notice}</div>}
      {error && <div className="rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>}

      <section className="card-surface overflow-hidden rounded-[14px]">
        <div className="border-b border-[#E8E8EE] px-5 py-5 sm:px-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <h2 className="font-display text-xl font-bold tracking-[-0.025em] text-[#1C1E25]">Your lead database</h2>
              <p className="mt-1 text-sm text-[#777A87]">Filter, enrich, select and export your best prospects without leaving this screen.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={!selectedCount || selectedCount > 100 || enriching}
                onClick={() => setEnrichOpen(true)}
                className="focus-ring inline-flex h-10 items-center gap-2 rounded-[9px] bg-[#14151C] px-3.5 text-sm font-bold text-white hover:bg-[#23252E] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Icon name="spark" className="h-4 w-4" /> {enriching ? 'Enriching…' : `Enrich${selectedCount ? ` ${selectedCount}` : ''}`}
              </button>
              <select value={exportFormat} onChange={(event) => setExportFormat(event.target.value as ExportFormat)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm text-[#4B4F5E]">
                <option value="xlsx">Excel (.xlsx)</option>
                <option value="csv">CSV (.csv)</option>
              </select>
              <button type="button" disabled={!exportCount || exporting} onClick={() => void exportLeads()} className="focus-ring inline-flex h-10 items-center gap-2 rounded-[9px] bg-[#7B61FF] px-3.5 text-sm font-bold text-white hover:bg-[#6E54EF] disabled:opacity-50">
                <Icon name="import" className="h-4 w-4" /> {exporting ? 'Exporting…' : `Export ${selectedCount ? `${selectedCount} selected` : 'view'}`}
              </button>
            </div>
          </div>

          <div className="mt-4 grid gap-2 lg:grid-cols-[1.4fr_1fr_0.8fr_0.65fr_auto]">
            <div className="relative">
              <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#92949E]" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search company, contact, email…" className="focus-ring h-10 w-full rounded-[9px] border border-[#DDDDE4] bg-white pl-9 pr-3 text-sm" />
            </div>
            <select value={selectedList} onChange={(event) => setSelectedList(event.target.value)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm text-[#3F424B]">
              <option value="all">All lead lists</option>
              {lists.map((list) => <option key={list.id} value={list.id}>{list.name} ({list.lead_count})</option>)}
            </select>
            <select value={emailFilter} onChange={(event) => setEmailFilter(event.target.value as EmailFilter)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm text-[#3F424B]">
              <option value="all">All email states</option>
              <option value="verified">Verified email</option>
              <option value="has_email">Has email</option>
              <option value="missing_email">Missing email</option>
            </select>
            <select value={minScore} onChange={(event) => setMinScore(event.target.value)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm text-[#3F424B]">
              <option value="0">Any score</option>
              <option value="70">70+</option>
              <option value="80">80+</option>
              <option value="85">85+</option>
              <option value="90">90+</option>
            </select>
            <button type="button" onClick={() => setRefreshKey((value) => value + 1)} className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm font-bold text-[#595C67] hover:bg-[#F8F8FA]">
              <Icon name="refresh" className="h-4 w-4" /> Refresh
            </button>
          </div>
          {selectedCount > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-[#71747F]">
              <span className="font-bold text-[#5E48C7]">{selectedCount} selected</span>
              <button type="button" onClick={() => setSelectedIds(new Set())} className="font-bold hover:text-[#7B61FF]">Clear selection</button>
              {selectedCount > 100 && <span className="text-[#A15C2F]">Enrichment runs are limited to 100 leads at a time. Export is unaffected.</span>}
            </div>
          )}
        </div>

        {loading ? (
          <div className="grid min-h-[300px] place-items-center text-sm font-medium text-[#747784]">Loading your leads…</div>
        ) : filtered.length === 0 ? (
          <div className="grid min-h-[320px] place-items-center px-6 text-center">
            <div className="max-w-[420px]">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-[12px] bg-[#F0EDFF] text-[#6D52EE]"><Icon name="users" className="h-5 w-5" /></div>
              <h3 className="mt-4 font-display text-lg font-bold text-[#25272E]">No matching leads</h3>
              <p className="mt-2 text-sm leading-6 text-[#777A87]">Adjust the filters or use Find Leads to discover another prospect list.</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1180px] border-collapse text-left">
              <thead className="bg-[#F8F8FA] text-[11px] font-bold uppercase tracking-[0.07em] text-[#777A87]">
                <tr>
                  <th className="w-12 px-5 py-3.5"><input aria-label="Select all visible leads" type="checkbox" checked={allFilteredSelected} onChange={toggleAllFiltered} /></th>
                  <th className="px-3 py-3.5">Company</th>
                  <th className="px-4 py-3.5">Contact</th>
                  <th className="px-4 py-3.5">Email</th>
                  <th className="px-4 py-3.5">Phone</th>
                  <th className="px-4 py-3.5">Score</th>
                  <th className="px-4 py-3.5">Source</th>
                  <th className="px-4 py-3.5">Links</th>
                  <th className="px-5 py-3.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ECECF1]">
                {filtered.map((lead) => {
                  const verified = lead.email && (lead.email_status || '').toLowerCase() === 'verified'
                  const contactName = [lead.first_name, lead.last_name].filter(Boolean).join(' ')
                  return (
                    <tr key={lead.id} className="bg-white text-sm hover:bg-[#FCFCFD]">
                      <td className="px-5 py-4"><input aria-label={`Select ${lead.company_name || lead.domain || 'lead'}`} type="checkbox" checked={selectedIds.has(lead.id)} onChange={() => toggleLead(lead.id)} /></td>
                      <td className="px-3 py-4">
                        <div className="font-semibold text-[#2D3038]">{lead.company_name || lead.domain || 'Unknown business'}</div>
                        <div className="mt-1 text-xs text-[#898C96]">{[lead.city, lead.region, lead.country].filter(Boolean).join(', ') || lead.domain || '—'}</div>
                      </td>
                      <td className="px-4 py-4">
                        {contactName || lead.job_title ? <><div className="font-medium text-[#343741]">{contactName || 'Decision maker'}</div><div className="mt-1 text-xs text-[#898C96]">{lead.job_title || 'Role unavailable'}</div></> : <span className="text-[#A0A2AA]">—</span>}
                      </td>
                      <td className="px-4 py-4">
                        {lead.email ? <div><div className="font-medium text-[#343741]">{lead.email}</div><div className={`mt-1 inline-flex rounded-md px-1.5 py-0.5 text-[10px] font-extrabold uppercase tracking-[0.05em] ${verified ? 'bg-[#F0F8DC] text-[#688328]' : 'bg-[#F2F1F6] text-[#80838D]'}`}>{verified ? 'Verified' : lead.email_status || 'Unverified'}</div></div> : <span className="text-[#A0A2AA]">—</span>}
                      </td>
                      <td className="px-4 py-4 text-[#50535D]">{lead.phone || '—'}</td>
                      <td className="px-4 py-4"><span className={`rounded-md px-2 py-1 text-[11px] font-extrabold ${(lead.score || 0) >= 85 ? 'bg-[#F0F8DC] text-[#668126]' : (lead.score || 0) >= 70 ? 'bg-[#F4F1FF] text-[#6753C8]' : 'bg-[#F3F3F5] text-[#777A87]'}`}>{lead.score ? Math.round(lead.score) : '—'}</span></td>
                      <td className="px-4 py-4"><span className="rounded-md bg-[#F2F1F6] px-2 py-1 text-[11px] font-bold text-[#676A75]">{lead.source === 'manual_search_import' ? 'Free import' : lead.source || 'Unknown'}</span></td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          {[
                            [lead.website, 'Web'], [lead.linkedin_url, 'in'], [lead.instagram_url, 'IG'], [lead.facebook_url, 'FB'],
                          ].filter(([url]) => Boolean(url)).map(([url, label]) => (
                            <a key={`${lead.id}-${label}`} href={url || '#'} target="_blank" rel="noreferrer" className="focus-ring grid h-7 min-w-7 place-items-center rounded-md border border-[#E0E0E6] px-1.5 text-[10px] font-extrabold text-[#6250BE] hover:bg-[#F6F4FF]">{label}</a>
                          ))}
                          {!lead.website && !lead.linkedin_url && !lead.instagram_url && !lead.facebook_url && <span className="text-[#A0A2AA]">—</span>}
                        </div>
                      </td>
                      <td className="px-5 py-4 text-right"><span className="rounded-md bg-[#F3F9E6] px-2 py-1 text-[10px] font-extrabold uppercase tracking-[0.06em] text-[#668126]">{lead.status}</span></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="flex items-center justify-between border-t border-[#E8E8EE] px-5 py-3 text-xs text-[#7A7D88] sm:px-6">
            <span>{filtered.length} lead{filtered.length === 1 ? '' : 's'} shown</span>
            <span>{lists.length} saved list{lists.length === 1 ? '' : 's'}</span>
          </div>
        )}
      </section>

      {enrichOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#14151C]/45 p-4" onMouseDown={(event) => { if (event.currentTarget === event.target && !enriching) setEnrichOpen(false) }}>
          <div className="w-full max-w-[560px] rounded-[16px] border border-white/20 bg-white p-6 shadow-2xl sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Data enrichment</p>
                <h3 className="mt-1 font-display text-xl font-bold text-[#22242B]">Prepare {selectedCount} lead{selectedCount === 1 ? '' : 's'} for outreach</h3>
              </div>
              <button type="button" onClick={() => setEnrichOpen(false)} className="focus-ring grid h-9 w-9 place-items-center rounded-lg text-[#777A87] hover:bg-[#F3F3F6]"><Icon name="close" className="h-4 w-4" /></button>
            </div>

            <label className="mt-6 block">
              <span className="mb-2 block text-[13px] font-semibold text-[#343741]">Provider</span>
              <select value={enrichProvider} onChange={(event) => setEnrichProvider(event.target.value as EnrichmentProvider)} className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-sm">
                <option value="auto">Smart — Prospeo then Apollo</option>
                <option value="prospeo">Prospeo only</option>
                <option value="apollo">Apollo only</option>
              </select>
            </label>

            <label className="mt-4 block">
              <span className="mb-2 block text-[13px] font-semibold text-[#343741]">Target roles</span>
              <input value={targetTitles} onChange={(event) => setTargetTitles(event.target.value)} className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] px-4 text-sm" />
              <p className="mt-2 text-xs leading-5 text-[#858894]">Comma-separated. We search these roles when the company was found but the decision-maker is missing.</p>
            </label>

            <div className="mt-5 rounded-[10px] bg-[#F8F7FC] px-4 py-3 text-xs leading-5 text-[#6E717D]">
              Enrichment can consume provider credits. Phone/mobile enrichment is intentionally disabled to avoid high-cost lookups. Verified work email and decision-maker details are the priority.
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setEnrichOpen(false)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] px-4 text-sm font-bold text-[#62656F]">Cancel</button>
              <button type="button" onClick={() => void runEnrichment()} className="focus-ring h-10 rounded-[9px] bg-[#7B61FF] px-4 text-sm font-bold text-white hover:bg-[#6D53EF]">Start enrichment</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
