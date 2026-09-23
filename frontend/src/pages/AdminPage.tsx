import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ApiRequestError,
  getAdminJobs,
  getAdminOverview,
  getAdminSystem,
  getAdminUsers,
  retryAdminJob,
  updateAdminUserStatus,
  type AdminJob,
  type AdminOverview,
  type AdminSystem,
  type AdminUser,
} from '../lib/api'
import { Icon } from '../components/Icon'

type Props = { getToken: () => Promise<string> }
type Tab = 'overview' | 'users' | 'jobs' | 'system'

function Stat({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return <div className="motion-card rounded-[13px] border border-[#E7E7ED] bg-white p-5 shadow-[0_8px_24px_rgba(20,21,28,0.035)]"><div className="text-xs font-bold uppercase tracking-[0.07em] text-[#8B8E99]">{label}</div><div className="mt-2 font-display text-2xl font-bold text-[#22242B]">{value}</div>{note&&<div className="mt-1 text-xs text-[#8A8D97]">{note}</div>}</div>
}

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? 'bg-[#8ACB35]' : 'bg-[#E06868]'}`} />
}

export function AdminPage({ getToken }: Props) {
  const [tab, setTab] = useState<Tab>('overview')
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [userTotal, setUserTotal] = useState(0)
  const [jobs, setJobs] = useState<AdminJob[]>([])
  const [jobTotal, setJobTotal] = useState(0)
  const [system, setSystem] = useState<AdminSystem | null>(null)
  const [search, setSearch] = useState('')
  const [userStatus, setUserStatus] = useState('')
  const [jobStatus, setJobStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)

  const load = useCallback(async (force = false) => {
    setLoading(true); setError(null)
    try {
      const token = await getToken()
      if (tab === 'overview') setOverview(await getAdminOverview(token, force))
      if (tab === 'users') { const data = await getAdminUsers(token, { search, status: userStatus }, force); setUsers(data.items); setUserTotal(data.total) }
      if (tab === 'jobs') { const data = await getAdminJobs(token, jobStatus, force); setJobs(data.items); setJobTotal(data.total) }
      if (tab === 'system') setSystem(await getAdminSystem(token, force))
      setUpdatedAt(new Date())
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not load admin data.')
    } finally { setLoading(false) }
  }, [getToken, tab, search, userStatus, jobStatus])

  useEffect(() => { void load() }, [load])

  const workerSummary = useMemo(() => system?.workers || [], [system])

  async function changeUserStatus(user: AdminUser) {
    const nextStatus = user.status === 'active' ? 'suspended' : 'active'
    const previous = users
    setUsers(current => current.map(item => item.firebase_uid === user.firebase_uid ? { ...item, status: nextStatus } : item))
    try {
      const token = await getToken()
      const updated = await updateAdminUserStatus(token, user.firebase_uid, nextStatus)
      setUsers(current => current.map(item => item.firebase_uid === updated.firebase_uid ? { ...item, ...updated } : item))
    } catch (next) {
      setUsers(previous)
      setError(next instanceof ApiRequestError ? next.message : 'Could not update this user.')
    }
  }

  async function retryJob(job: AdminJob) {
    const previous = jobs
    setJobs(current => current.map(item => item.id === job.id ? { ...item, status: 'pending', last_error: null } : item))
    try {
      const token = await getToken()
      const updated = await retryAdminJob(token, job.id)
      setJobs(current => current.map(item => item.id === updated.id ? { ...item, ...updated } : item))
    } catch (next) {
      setJobs(previous)
      setError(next instanceof ApiRequestError ? next.message : 'Could not retry the job.')
    }
  }

  return <div className="space-y-5">
    <section className="card-surface rounded-[14px] p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Operations</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Platform administration</h2><p className="mt-1 text-sm text-[#777A87]">Users, jobs, provider activity and production health in one place.</p></div>
        <button onClick={() => void load(true)} disabled={loading} className="button-pop inline-flex items-center gap-2 rounded-[9px] border border-[#DDDDE4] bg-white px-3.5 py-2.5 text-sm font-bold text-[#555966] disabled:opacity-50"><Icon name="refresh" className={`h-4 w-4 ${loading?'animate-spin':''}`} /> Refresh</button>
      </div>
      <div className="mt-5 flex flex-wrap gap-1 rounded-[10px] bg-[#F4F4F7] p-1">{(['overview','users','jobs','system'] as Tab[]).map(item=><button key={item} onClick={()=>setTab(item)} className={`rounded-[8px] px-3.5 py-2 text-sm font-bold capitalize transition ${tab===item?'bg-white text-[#14151C] shadow-sm':'text-[#70737D] hover:text-[#292B32]'}`}>{item}</button>)}</div>
      {updatedAt&&<div className="mt-3 text-right text-[11px] text-[#9699A3]">Updated {updatedAt.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}</div>}
    </section>

    {error&&<div className="rounded-[10px] border border-[#F2CACA] bg-[#FFF7F7] px-4 py-3 text-sm font-semibold text-[#B54B4B]">{error}</div>}

    {tab==='overview' && overview && <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Stat label="Users" value={overview.users_total} note={`${overview.users_active} active`} /><Stat label="Leads" value={overview.leads_total} note={`${overview.lead_lists_total} lists`} /><Stat label="Emails sent" value={overview.emails_sent} note={`${overview.replies_total} replies`} /><Stat label="Failed jobs" value={overview.jobs_failed} note={`${overview.jobs_running} running`} /></div>
      <div className="grid gap-4 lg:grid-cols-2"><section className="card-surface rounded-[14px] p-5"><h3 className="font-display text-lg font-bold text-[#292B32]">Discovery usage</h3><div className="mt-4 grid grid-cols-3 gap-3"><Stat label="Search calls" value={overview.search_calls} /><Stat label="Sites checked" value={overview.websites_checked} /><Stat label="Enriched" value={overview.enriched_contacts} /></div></section><section className="card-surface rounded-[14px] p-5"><h3 className="font-display text-lg font-bold text-[#292B32]">Connections</h3><div className="mt-5 flex items-center justify-between border-b border-[#ECECF1] pb-3 text-sm"><span className="text-[#6E717B]">Provider connections</span><strong>{overview.connected_providers}</strong></div><div className="mt-3 flex items-center justify-between text-sm"><span className="text-[#6E717B]">Email senders</span><strong>{overview.connected_senders}</strong></div></section></div>
    </div>}

    {tab==='users' && <section className="card-surface overflow-hidden rounded-[14px]"><div className="flex flex-col gap-3 border-b border-[#E8E8EE] p-5 sm:flex-row"><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search user…" className="focus-ring h-10 flex-1 rounded-[9px] border border-[#DDDDE4] px-3 text-sm"/><select value={userStatus} onChange={e=>setUserStatus(e.target.value)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option></select><button onClick={()=>void load(true)} className="rounded-[9px] bg-[#14151C] px-4 py-2 text-sm font-bold text-white">Apply</button></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-[#F8F8FA] text-xs uppercase tracking-[0.05em] text-[#858894]"><tr><th className="px-5 py-3">User</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Leads</th><th className="px-5 py-3">Campaigns</th><th className="px-5 py-3">Last login</th><th className="px-5 py-3">Status</th><th className="px-5 py-3"></th></tr></thead><tbody className="divide-y divide-[#ECECF1]">{users.map(user=><tr key={user.firebase_uid} className="motion-row"><td className="px-5 py-4"><div className="font-bold text-[#30323A]">{user.display_name||'Unnamed user'}</div><div className="mt-0.5 text-xs text-[#888B95]">{user.email||user.firebase_uid}</div></td><td className="px-5 py-4 capitalize">{user.role}</td><td className="px-5 py-4">{user.lead_count}</td><td className="px-5 py-4">{user.campaign_count}</td><td className="px-5 py-4 text-xs text-[#777A84]">{new Date(user.last_login_at).toLocaleString()}</td><td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase ${user.status==='active'?'bg-[#F1F8E6] text-[#61842D]':'bg-[#FFF0F0] text-[#B25454]'}`}>{user.status}</span></td><td className="px-5 py-4 text-right"><button onClick={()=>void changeUserStatus(user)} className="rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#555966]">{user.status==='active'?'Suspend':'Reactivate'}</button></td></tr>)}{!users.length&&<tr><td colSpan={7} className="p-10 text-center text-[#8A8D97]">No users found.</td></tr>}</tbody></table></div><div className="border-t border-[#ECECF1] px-5 py-3 text-xs text-[#8A8D97]">{userTotal} total users</div></section>}

    {tab==='jobs' && <section className="card-surface overflow-hidden rounded-[14px]"><div className="flex items-center gap-3 border-b border-[#E8E8EE] p-5"><select value={jobStatus} onChange={e=>setJobStatus(e.target.value)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">All jobs</option><option value="pending">Pending</option><option value="running">Running</option><option value="failed">Failed</option><option value="complete">Complete</option></select><button onClick={()=>void load(true)} className="rounded-[9px] bg-[#14151C] px-4 py-2 text-sm font-bold text-white">Apply</button></div><div className="divide-y divide-[#ECECF1]">{jobs.map(job=><div key={job.id} className="motion-row flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between"><div><div className="flex flex-wrap items-center gap-2"><span className="font-bold text-[#30323A]">{job.job_type.replaceAll('_',' ')}</span><span className="rounded-full bg-[#F2F1F6] px-2.5 py-1 text-[10px] font-extrabold uppercase text-[#686B75]">{job.status}</span></div><div className="mt-1 text-xs text-[#898C96]">{job.user_email||job.user_id} · attempt {job.attempt_count}/{job.max_attempts}</div>{job.last_error&&<div className="mt-2 max-w-3xl text-xs text-[#B25555]">{job.last_error}</div>}</div>{job.status==='failed'&&job.attempt_count<job.max_attempts&&<button onClick={()=>void retryJob(job)} className="rounded-[8px] border border-[#D9D4F7] px-3 py-2 text-xs font-bold text-[#6B54D7]">Retry</button>}</div>)}{!jobs.length&&<div className="p-10 text-center text-[#8A8D97]">No jobs found.</div>}</div><div className="border-t border-[#ECECF1] px-5 py-3 text-xs text-[#8A8D97]">{jobTotal} total jobs</div></section>}

    {tab==='system' && system && <div className="grid gap-4 lg:grid-cols-2"><section className="card-surface rounded-[14px] p-5"><h3 className="font-display text-lg font-bold text-[#292B32]">Core services</h3><div className="mt-4 space-y-3 text-sm"><div className="flex items-center justify-between"><span className="flex items-center gap-2"><StatusDot ok={system.database_ok}/>Database</span><strong>{system.database_ok?'Healthy':'Unavailable'}</strong></div><div className="flex items-center justify-between"><span>Environment</span><strong>{system.environment}</strong></div><div className="flex items-center justify-between"><span>API</span><strong>{system.api_version}</strong></div><div className="flex items-center justify-between"><span>Background mode</span><strong>{system.background_jobs_mode}</strong></div><div className="flex items-center justify-between"><span>Public API URL</span><strong>{system.public_api_configured?'Configured':'Missing'}</strong></div><div className="flex items-center justify-between"><span>Hostinger live webhooks</span><strong>{system.hostinger_webhooks_configured}</strong></div></div></section><section className="card-surface rounded-[14px] p-5"><h3 className="font-display text-lg font-bold text-[#292B32]">Workers</h3><div className="mt-4 space-y-3">{workerSummary.map(worker=><div key={worker.worker_name} className="flex items-center justify-between rounded-[9px] bg-[#F8F8FA] px-3 py-3 text-sm"><span className="flex items-center gap-2"><StatusDot ok={worker.healthy}/>{worker.worker_name}</span><span className="text-xs text-[#858894]">{worker.healthy?'Online':'Stale'}</span></div>)}{!workerSummary.length&&<div className="text-sm text-[#858894]">No worker heartbeat recorded yet.</div>}</div></section><section className="card-surface rounded-[14px] p-5 lg:col-span-2"><h3 className="font-display text-lg font-bold text-[#292B32]">Provider health</h3><div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{system.providers.map(provider=><div key={provider.provider} className="rounded-[10px] border border-[#E7E7ED] p-4"><div className="font-bold capitalize text-[#33353D]">{provider.provider}</div><div className="mt-2 text-xs text-[#7E818C]">{provider.connected_count} connected · {provider.error_count} errors</div></div>)}{!system.providers.length&&<div className="text-sm text-[#858894]">No provider connections yet.</div>}</div></section></div>}

    {loading&&!overview&&tab==='overview'&&<div className="card-surface rounded-[14px] p-10 text-center text-sm text-[#858894]">Loading admin dashboard…</div>}
  </div>
}
