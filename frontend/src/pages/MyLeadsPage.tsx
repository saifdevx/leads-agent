import { useEffect, useMemo, useState } from 'react'
import { Icon } from '../components/Icon'
import { ApiRequestError, getLeadLists, getLeads, type Lead, type LeadList } from '../lib/api'

type Props = { getToken: () => Promise<string> }

export function MyLeadsPage({ getToken }: Props) {
  const [lists, setLists] = useState<LeadList[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [selectedList, setSelectedList] = useState('all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

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
    if (!needle) return leads
    return leads.filter((lead) => [lead.company_name, lead.email, lead.phone, lead.website, lead.region, lead.domain]
      .some((value) => value?.toLowerCase().includes(needle)))
  }, [leads, search])

  return (
    <div className="space-y-5">
      <section className="card-surface overflow-hidden rounded-[14px]">
        <div className="border-b border-[#E8E8EE] px-5 py-5 sm:px-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="font-display text-xl font-bold tracking-[-0.025em] text-[#1C1E25]">Your lead database</h2>
              <p className="mt-1 text-sm text-[#777A87]">All contacts discovered through free and connected sources will appear here.</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative min-w-[220px]">
                <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#92949E]" />
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search leads…" className="focus-ring h-10 w-full rounded-[9px] border border-[#DDDDE4] bg-white pl-9 pr-3 text-sm" />
              </div>
              <select value={selectedList} onChange={(event) => setSelectedList(event.target.value)} className="focus-ring h-10 min-w-[210px] rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm text-[#3F424B]">
                <option value="all">All lead lists</option>
                {lists.map((list) => <option key={list.id} value={list.id}>{list.name} ({list.lead_count})</option>)}
              </select>
              <button type="button" onClick={() => setRefreshKey((value) => value + 1)} className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm font-bold text-[#595C67] hover:bg-[#F8F8FA]">
                <Icon name="refresh" className="h-4 w-4" /> Refresh
              </button>
            </div>
          </div>
        </div>

        {error ? (
          <div className="m-5 rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>
        ) : loading ? (
          <div className="grid min-h-[300px] place-items-center text-sm font-medium text-[#747784]">Loading your leads…</div>
        ) : filtered.length === 0 ? (
          <div className="grid min-h-[320px] place-items-center px-6 text-center">
            <div className="max-w-[420px]">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-[12px] bg-[#F0EDFF] text-[#6D52EE]"><Icon name="users" className="h-5 w-5" /></div>
              <h3 className="mt-4 font-display text-lg font-bold text-[#25272E]">No matching leads yet</h3>
              <p className="mt-2 text-sm leading-6 text-[#777A87]">Use Find Leads to create free search queries, paste your search results, and save extracted contacts here.</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] border-collapse text-left">
              <thead className="bg-[#F8F8FA] text-[11px] font-bold uppercase tracking-[0.07em] text-[#777A87]">
                <tr>
                  <th className="px-5 py-3.5">Company</th>
                  <th className="px-4 py-3.5">Email</th>
                  <th className="px-4 py-3.5">Phone</th>
                  <th className="px-4 py-3.5">Location</th>
                  <th className="px-4 py-3.5">Source</th>
                  <th className="px-4 py-3.5">Links</th>
                  <th className="px-5 py-3.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ECECF1]">
                {filtered.map((lead) => (
                  <tr key={lead.id} className="bg-white text-sm hover:bg-[#FCFCFD]">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-[#2D3038]">{lead.company_name || lead.domain || 'Unknown business'}</div>
                      {lead.website && <a href={lead.website} target="_blank" rel="noreferrer" className="mt-1 block max-w-[220px] truncate text-xs font-medium text-[#755BE8] hover:underline">{lead.domain || lead.website}</a>}
                    </td>
                    <td className="px-4 py-4">
                      {lead.email ? <div><div className="font-medium text-[#343741]">{lead.email}</div><div className="mt-1 text-[10px] font-bold uppercase tracking-[0.06em] text-[#8A8D97]">{lead.email_status || 'unverified'}</div></div> : <span className="text-[#A0A2AA]">—</span>}
                    </td>
                    <td className="px-4 py-4 text-[#50535D]">{lead.phone || '—'}</td>
                    <td className="px-4 py-4 text-[#50535D]">{[lead.city, lead.region, lead.country].filter(Boolean).join(', ') || '—'}</td>
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
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="flex items-center justify-between border-t border-[#E8E8EE] px-5 py-3 text-xs text-[#7A7D88] sm:px-6">
            <span>{filtered.length} lead{filtered.length === 1 ? '' : 's'} shown</span>
            <span>{lists.length} saved list{lists.length === 1 ? '' : 's'}</span>
          </div>
        )}
      </section>
    </div>
  )
}
