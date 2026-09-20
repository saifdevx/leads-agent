import { useEffect, useMemo, useState } from 'react'
import { Icon } from '../components/Icon'
import {
  ApiRequestError,
  campaignAction,
  connectHostingerSender,
  createCampaign,
  deleteCampaign,
  deleteTemplate,
  disconnectSender,
  getCampaigns,
  getGmailAuthorizeUrl,
  getSenders,
  getTemplates,
  quickSend,
  saveTemplate,
  suppressEmail,
  type Campaign,
  type CampaignCreateResult,
  type EmailTemplate,
  type SenderConnection,
} from '../lib/api'

type Props = {
  getToken: () => Promise<string>
  initialLeadIds: string[]
  onClearInitialLeadIds: () => void
  onOpenLeads: () => void
}

type Tab = 'campaigns' | 'quick' | 'templates' | 'senders'

const sampleTemplate = {
  name: 'Simple introduction',
  category: 'General',
  subject: 'Quick question for {{company_name}}',
  body: `Hi {{first_name}},\n\nI came across {{company_name}} while researching businesses in {{location}}.\n\nI wanted to reach out with a quick idea that may be useful for your team.\n\nWould you be open to a short conversation?\n\nIf you'd rather not receive messages from me, reply unsubscribe.\n\nBest,\n{{sender_name}}`,
}

function statusClasses(status: string) {
  if (status === 'completed') return 'bg-[#F0F8DC] text-[#688328]'
  if (status === 'sending') return 'bg-[#F0EDFF] text-[#6753C8]'
  if (status === 'failed') return 'bg-[#FFF0EE] text-[#9D3D36]'
  if (status === 'paused') return 'bg-[#FFF7E8] text-[#9B6A20]'
  if (status === 'cancelled') return 'bg-[#F3F3F5] text-[#777A87]'
  return 'bg-[#F3F2F7] text-[#6D6F79]'
}

function scheduleLabel(campaign: Campaign) {
  if (campaign.send_start_hour === 0 && campaign.send_end_hour === 24) return 'Send anytime'
  const start = String(campaign.send_start_hour).padStart(2, '0')
  const end = String(campaign.send_end_hour).padStart(2, '0')
  return `${start}:00–${end}:00 ${campaign.timezone}`
}

export function OutreachPage({ getToken, initialLeadIds, onClearInitialLeadIds, onOpenLeads }: Props) {
  const [tab, setTab] = useState<Tab>('campaigns')
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [senders, setSenders] = useState<SenderConnection[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  const [templateForm, setTemplateForm] = useState(sampleTemplate)
  const [editingTemplate, setEditingTemplate] = useState<string | undefined>()
  const [savingTemplate, setSavingTemplate] = useState(false)

  const [connectingGmail, setConnectingGmail] = useState(false)
  const [connectingHostinger, setConnectingHostinger] = useState(false)
  const [hostingerToken, setHostingerToken] = useState('')
  const [hostingerMailbox, setHostingerMailbox] = useState('')
  const [hostingerDisplayName, setHostingerDisplayName] = useState('')

  const [creatingCampaign, setCreatingCampaign] = useState(false)
  const [campaignResult, setCampaignResult] = useState<CampaignCreateResult | null>(null)
  const [campaignName, setCampaignName] = useState('New outreach campaign')
  const [templateId, setTemplateId] = useState('')
  const [senderId, setSenderId] = useState('')
  const [dailyLimit, setDailyLimit] = useState(30)
  const [intervalSeconds, setIntervalSeconds] = useState(30)
  const [useSendingWindow, setUseSendingWindow] = useState(false)
  const [startHour, setStartHour] = useState(9)
  const [endHour, setEndHour] = useState(17)
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

  const [quickSenderId, setQuickSenderId] = useState('')
  const [quickTo, setQuickTo] = useState('')
  const [quickSubject, setQuickSubject] = useState('Test from Lead Platform')
  const [quickBody, setQuickBody] = useState('This is a test message from Lead Platform.')
  const [quickSending, setQuickSending] = useState(false)

  const [suppressAddress, setSuppressAddress] = useState('')

  async function load(showLoader = true) {
    if (showLoader) setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const [nextTemplates, nextSenders, nextCampaigns] = await Promise.all([
        getTemplates(token), getSenders(token), getCampaigns(token),
      ])
      setTemplates(nextTemplates)
      setSenders(nextSenders)
      setCampaigns(nextCampaigns)
      setTemplateId((current) => current || nextTemplates[0]?.id || '')
      setSenderId((current) => current || nextSenders[0]?.id || '')
      setQuickSenderId((current) => current || nextSenders[0]?.id || '')
      setLastRefreshed(new Date())
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not load outreach.')
    } finally {
      if (showLoader) setLoading(false)
    }
  }

  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!campaigns.some((campaign) => campaign.status === 'sending')) return
    const timer = window.setInterval(() => { void load(false) }, 15000)
    return () => window.clearInterval(timer)
  }, [campaigns.some((campaign) => campaign.status === 'sending')]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const gmail = params.get('gmail')
    if (gmail === 'connected') {
      setNotice('Gmail sender connected successfully.')
      setTab('senders')
      params.delete('gmail')
      window.history.replaceState({}, '', `${window.location.pathname}${params.toString() ? `?${params}` : ''}`)
      void load(false)
    } else if (gmail === 'error') {
      setError('Gmail connection did not complete. Check the OAuth configuration and try again.')
      setTab('senders')
      params.delete('gmail')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const totals = useMemo(() => campaigns.reduce((acc, campaign) => ({
    campaigns: acc.campaigns + 1,
    recipients: acc.recipients + campaign.recipient_count,
    sent: acc.sent + campaign.sent_count,
    failed: acc.failed + campaign.failed_count,
  }), { campaigns: 0, recipients: 0, sent: 0, failed: 0 }), [campaigns])

  async function handleSaveTemplate() {
    setSavingTemplate(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      await saveTemplate(token, templateForm, editingTemplate)
      setTemplateForm(sampleTemplate); setEditingTemplate(undefined); setNotice('Template saved.'); await load(false)
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not save template.') }
    finally { setSavingTemplate(false) }
  }

  async function handleConnectGmail() {
    setConnectingGmail(true); setError(null)
    try {
      const token = await getToken(); window.location.href = await getGmailAuthorizeUrl(token)
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not start Gmail authorization.'); setConnectingGmail(false)
    }
  }

  async function handleConnectHostinger() {
    if (!hostingerToken.trim()) return
    setConnectingHostinger(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      const sender = await connectHostingerSender(token, {
        api_token: hostingerToken.trim(), mailbox_email: hostingerMailbox.trim() || undefined,
        display_name: hostingerDisplayName.trim() || undefined,
      })
      setHostingerToken(''); setHostingerMailbox(''); setHostingerDisplayName('')
      setNotice(`Hostinger mailbox ${sender.email} connected successfully.`)
      await load(false); setSenderId(sender.id); setQuickSenderId(sender.id)
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not connect Hostinger Mail.') }
    finally { setConnectingHostinger(false) }
  }

  async function handleCreateCampaign() {
    if (!initialLeadIds.length) return
    if (useSendingWindow && startHour === endHour) {
      setError('Choose different start and end hours, or turn the sending window off.')
      return
    }
    setCreatingCampaign(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      const result = await createCampaign(token, {
        name: campaignName, lead_ids: initialLeadIds, template_id: templateId, sender_id: senderId,
        daily_limit: dailyLimit,
        send_start_hour: useSendingWindow ? startHour : 0,
        send_end_hour: useSendingWindow ? endHour : 24,
        timezone,
        min_interval_seconds: intervalSeconds,
      })
      setCampaignResult(result); setNotice('Draft created. Review the preview before approving.'); onClearInitialLeadIds(); await load(false)
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not create campaign.') }
    finally { setCreatingCampaign(false) }
  }

  async function handleQuickSend() {
    if (!quickSenderId || !quickTo.trim() || !quickSubject.trim() || !quickBody.trim()) return
    setQuickSending(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      const result = await quickSend(token, {
        sender_id: quickSenderId, to_email: quickTo.trim(), subject: quickSubject.trim(), body: quickBody,
      })
      setNotice(`Test email sent from ${result.sender_email} to ${result.to_email}.`)
      setQuickTo('')
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not send the test email.')
    } finally { setQuickSending(false) }
  }

  async function act(campaignId: string, action: 'approve'|'pause'|'resume'|'cancel') {
    setError(null); setNotice(null)
    try {
      const token = await getToken(); await campaignAction(token, campaignId, action)
      setNotice(action === 'approve' ? 'Campaign approved and queued for sending.' : `Campaign ${action}d.`)
      setCampaignResult(null); await load(false)
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not update campaign.') }
  }

  async function removeCampaign(campaignId: string) {
    if (!window.confirm('Delete this campaign and its message records? This cannot be undone.')) return
    setError(null); setNotice(null)
    try {
      const token = await getToken(); await deleteCampaign(token, campaignId); setNotice('Campaign deleted.'); await load(false)
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not delete campaign.') }
  }

  return <div className="space-y-5">
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[
        ['Campaigns', totals.campaigns, 'Saved outreach'], ['Recipients', totals.recipients, 'Across campaigns'],
        ['Sent', totals.sent, 'Accepted by sender API'], ['Failed', totals.failed, 'Needs review'],
      ].map(([label, value, helper]) => <div key={String(label)} className="card-surface rounded-[12px] px-5 py-4">
        <div className="text-xs font-bold uppercase tracking-[0.07em] text-[#858894]">{label}</div>
        <div className="mt-1 font-display text-2xl font-bold text-[#1F2128]">{value}</div>
        <div className="mt-1 text-xs text-[#8A8D97]">{helper}</div>
      </div>)}
    </section>

    {notice && <div className="rounded-[10px] border border-[#DDE9B9] bg-[#F7FBEA] px-4 py-3 text-sm font-medium text-[#59731C]">{notice}</div>}
    {error && <div className="rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>}

    <section className="card-surface rounded-[14px] p-2">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1">
          {(['campaigns','quick','templates','senders'] as Tab[]).map((item) => <button key={item} onClick={() => setTab(item)} className={`focus-ring rounded-[9px] px-4 py-2.5 text-sm font-bold capitalize ${tab===item?'bg-[#14151C] text-white':'text-[#666A76] hover:bg-[#F4F3F8]'}`}>{item === 'quick' ? 'Quick send' : item}</button>)}
        </div>
        <div className="flex items-center gap-2 px-1">
          {lastRefreshed && <span className="hidden text-[11px] text-[#9699A2] md:inline">Updated {lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
          <button disabled={loading} onClick={() => void load(false)} className="focus-ring inline-flex h-9 items-center gap-2 rounded-[8px] border border-[#DDDDE4] bg-white px-3 text-xs font-bold text-[#555966] hover:bg-[#F8F8FA] disabled:opacity-50"><Icon name="refresh" className="h-3.5 w-3.5" /> Refresh</button>
        </div>
      </div>
    </section>

    {tab === 'campaigns' && <div className="space-y-5">
      <section className="card-surface rounded-[14px] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Create campaign</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Send to selected leads</h2><p className="mt-1 text-sm text-[#777A87]">Select leads, choose a sender and approve the preview. Sending starts immediately unless you enable a time window.</p></div>
          {!initialLeadIds.length && <button onClick={onOpenLeads} className="focus-ring rounded-[9px] border border-[#DCDDE5] bg-white px-4 py-2.5 text-sm font-bold text-[#4B4F5E] hover:bg-[#F8F8FA]">Select leads</button>}
        </div>
        {initialLeadIds.length > 0 && <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Campaign name</span><input value={campaignName} onChange={e=>setCampaignName(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Template</span><select value={templateId} onChange={e=>setTemplateId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose template</option>{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender</span><select value={senderId} onChange={e=>setSenderId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose sender</option>{senders.map(s=><option key={s.id} value={s.id}>{s.email} · {s.provider === 'hostinger' ? 'Hostinger' : 'Gmail'}</option>)}</select></label>
          <div className="grid grid-cols-2 gap-3"><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Daily limit</span><input type="number" min={1} max={200} value={dailyLimit} onChange={e=>setDailyLimit(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Send interval</span><select value={intervalSeconds} onChange={e=>setIntervalSeconds(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value={20}>20 sec</option><option value={30}>30 sec</option><option value={45}>45 sec</option><option value={60}>60 sec</option><option value={90}>90 sec</option><option value={120}>2 min</option></select></label></div>
          <div className="lg:col-span-2 rounded-[10px] border border-[#E7E5F0] bg-[#FAF9FD] p-4">
            <label className="flex cursor-pointer items-center justify-between gap-4"><div><div className="text-sm font-bold text-[#343741]">Limit sending to certain hours</div><div className="mt-1 text-xs text-[#858894]">Optional. Leave off to begin sending as soon as you approve the campaign.</div></div><input type="checkbox" checked={useSendingWindow} onChange={e=>setUseSendingWindow(e.target.checked)} className="h-4 w-4 accent-[#7B61FF]" /></label>
            {useSendingWindow && <div className="mt-4 grid grid-cols-2 gap-3"><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Start hour</span><input type="number" min={0} max={23} value={startHour} onChange={e=>setStartHour(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">End hour</span><input type="number" min={1} max={24} value={endHour} onChange={e=>setEndHour(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm" /></label><div className="col-span-2 text-xs text-[#858894]">24-hour clock · {timezone}. Example: 9 to 17 means 9 AM–5 PM.</div></div>}
          </div>
          <div className="lg:col-span-2 flex flex-col gap-3 rounded-[10px] bg-[#F6F5FA] px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div><div className="text-sm font-bold text-[#343741]">{initialLeadIds.length} selected lead{initialLeadIds.length===1?'':'s'}</div><div className="text-xs text-[#858894]">{useSendingWindow ? `Window ${startHour}:00–${endHour}:00 ${timezone}` : 'Starts after approval'} · every {intervalSeconds}s · missing/suppressed addresses skipped.</div></div><button disabled={!templateId||!senderId||creatingCampaign} onClick={handleCreateCampaign} className="focus-ring rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#6D53F0] disabled:opacity-40">{creatingCampaign?'Preparing…':'Preview campaign'}</button></div>
        </div>}
      </section>

      {campaignResult && <section className="rounded-[14px] border border-[#DCD7FF] bg-[#FBFAFF] p-6"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Approval required</p><h3 className="mt-1 font-display text-lg font-bold text-[#22242B]">Review before sending</h3><p className="mt-1 text-sm text-[#777A87]">{campaignResult.campaign.recipient_count} recipients · {campaignResult.suppressed_count} suppressed · {campaignResult.missing_email_count} missing email</p></div><button onClick={()=>act(campaignResult.campaign.id,'approve')} className="focus-ring rounded-[9px] bg-[#14151C] px-4 py-2.5 text-sm font-bold text-white">Approve & queue</button></div><div className="mt-4 grid gap-3 xl:grid-cols-3">{campaignResult.preview.map(item=><div key={item.lead_id} className="rounded-[10px] border border-[#E4E2EF] bg-white p-4"><div className="text-xs font-bold text-[#7A7D88]">To: {item.to_email}</div><div className="mt-2 text-sm font-bold text-[#2C2F37]">{item.subject}</div><pre className="mt-2 whitespace-pre-wrap font-sans text-xs leading-5 text-[#686B75]">{item.body}</pre></div>)}</div></section>}

      <section className="card-surface overflow-hidden rounded-[14px]"><div className="border-b border-[#E8E8EE] px-6 py-5"><h2 className="font-display text-xl font-bold text-[#1C1E25]">Campaigns</h2><p className="mt-1 text-sm text-[#777A87]">Live progress, pause/resume controls and quick cleanup for test campaigns.</p></div>{loading?<div className="p-6 text-sm text-[#777A87]">Loading…</div>:campaigns.length===0?<div className="p-8 text-center text-sm text-[#858894]">No campaigns yet.</div>:<div className="divide-y divide-[#ECECF1]">{campaigns.map(c=>{const progress=c.recipient_count?Math.min(100,Math.round(((c.sent_count+c.failed_count+c.skipped_count)/c.recipient_count)*100)):0;return <div key={c.id} className="px-6 py-4"><div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="font-bold text-[#2D3038]">{c.name}</span><span className={`rounded-md px-2 py-1 text-[10px] font-extrabold uppercase ${statusClasses(c.status)}`}>{c.status}</span></div><div className="mt-1 text-xs text-[#858894]">{c.sender_email || 'Sender'} · {c.sent_count}/{c.recipient_count} sent · {c.failed_count} failed · every {c.min_interval_seconds}s</div><div className="mt-1 text-[11px] text-[#999BA4]">{scheduleLabel(c)}</div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#ECEBF1]"><div className="h-full rounded-full bg-[#7B61FF] transition-all" style={{width:`${progress}%`}} /></div></div><div className="flex flex-wrap gap-2">{c.status==='draft'&&<button onClick={()=>act(c.id,'approve')} className="rounded-[8px] bg-[#7B61FF] px-3 py-2 text-xs font-bold text-white">Approve</button>}{c.status==='sending'&&<button onClick={()=>act(c.id,'pause')} className="rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#555966]">Pause</button>}{c.status==='paused'&&<button onClick={()=>act(c.id,'resume')} className="rounded-[8px] bg-[#14151C] px-3 py-2 text-xs font-bold text-white">Resume</button>}{!['completed','cancelled'].includes(c.status)&&<button onClick={()=>act(c.id,'cancel')} className="rounded-[8px] border border-[#F0CBC8] px-3 py-2 text-xs font-bold text-[#9D3D36]">Cancel</button>}{c.status!=='sending'&&<button onClick={()=>void removeCampaign(c.id)} className="rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#777A87]">Delete</button>}</div></div></div>})}</div>}</section>
    </div>}

    {tab === 'quick' && <section className="card-surface rounded-[14px] p-6">
      <div className="max-w-3xl"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">One-off message</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Quick send</h2><p className="mt-1 text-sm leading-6 text-[#777A87]">Useful for testing a sender or sending a single custom email. This sends immediately when you click Send, so review the address and content first.</p></div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender</span><select value={quickSenderId} onChange={e=>setQuickSenderId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose sender</option>{senders.map(s=><option key={s.id} value={s.id}>{s.email} · {s.provider === 'hostinger' ? 'Hostinger' : 'Gmail'}</option>)}</select></label>
        <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Recipient email</span><input type="email" value={quickTo} onChange={e=>setQuickTo(e.target.value)} placeholder="you@example.com" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
        <label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Subject</span><input value={quickSubject} onChange={e=>setQuickSubject(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
        <label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Message</span><textarea rows={9} value={quickBody} onChange={e=>setQuickBody(e.target.value)} className="focus-ring w-full rounded-[9px] border border-[#DDDDE4] p-3 text-sm" /></label>
      </div>
      <div className="mt-4 flex flex-col gap-3 rounded-[10px] bg-[#F8F7FC] px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div className="text-xs leading-5 text-[#6E717D]">Suppressed addresses are blocked. Quick Send is intentionally limited to one recipient at a time.</div><button disabled={quickSending||!quickSenderId||!quickTo.trim()||!quickSubject.trim()||!quickBody.trim()} onClick={()=>void handleQuickSend()} className="focus-ring inline-flex items-center justify-center gap-2 rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40"><Icon name="mail" className="h-4 w-4" /> {quickSending?'Sending…':'Send now'}</button></div>
    </section>}

    {tab === 'templates' && <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]"><section className="card-surface rounded-[14px] p-6"><h2 className="font-display text-xl font-bold text-[#22242B]">Email template</h2><p className="mt-1 text-sm text-[#777A87]">Supported: {'{{first_name}}'}, {'{{company_name}}'}, {'{{job_title}}'}, {'{{location}}'}, {'{{website}}'}, {'{{sender_name}}'}.</p><div className="mt-5 space-y-4"><input value={templateForm.name} onChange={e=>setTemplateForm({...templateForm,name:e.target.value})} placeholder="Template name" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><input value={templateForm.category} onChange={e=>setTemplateForm({...templateForm,category:e.target.value})} placeholder="Category" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><input value={templateForm.subject} onChange={e=>setTemplateForm({...templateForm,subject:e.target.value})} placeholder="Subject" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><textarea value={templateForm.body} onChange={e=>setTemplateForm({...templateForm,body:e.target.value})} rows={11} className="focus-ring w-full rounded-[9px] border border-[#DDDDE4] p-3 text-sm" /><button disabled={savingTemplate} onClick={handleSaveTemplate} className="focus-ring rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white">{savingTemplate?'Saving…':editingTemplate?'Update template':'Save template'}</button></div></section><section className="card-surface overflow-hidden rounded-[14px]"><div className="border-b border-[#E8E8EE] px-6 py-5"><h2 className="font-display text-xl font-bold text-[#22242B]">Saved templates</h2></div><div className="divide-y divide-[#ECECF1]">{templates.map(t=><div key={t.id} className="p-5"><div className="flex items-start justify-between gap-3"><div><div className="font-bold text-[#2D3038]">{t.name}</div><div className="mt-1 text-xs text-[#858894]">{t.category} · {t.subject}</div></div><div className="flex gap-2"><button onClick={()=>{setEditingTemplate(t.id);setTemplateForm({name:t.name,category:t.category,subject:t.subject,body:t.body})}} className="rounded-md border border-[#DDDDE4] px-2.5 py-1.5 text-xs font-bold">Edit</button><button onClick={async()=>{const token=await getToken();await deleteTemplate(token,t.id);await load(false)}} className="rounded-md border border-[#F0CBC8] px-2.5 py-1.5 text-xs font-bold text-[#9D3D36]">Delete</button></div></div></div>)}{!templates.length&&<div className="p-8 text-center text-sm text-[#858894]">Create your first template.</div>}</div></section></div>}

    {tab === 'senders' && <div className="space-y-5">
      <section className="card-surface rounded-[14px] p-6"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Recommended sender</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Hostinger Mail</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-[#777A87]">Paste the Agentic Mail API token you created in Hostinger. The backend validates it, discovers the mailbox, encrypts the token and never returns the plaintext value.</p></div><div className="mt-5 grid gap-4 lg:grid-cols-2"><label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Hostinger API token</span><input type="password" autoComplete="off" value={hostingerToken} onChange={e=>setHostingerToken(e.target.value)} placeholder="Paste token once" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Mailbox email <span className="font-medium text-[#9598A2]">(optional)</span></span><input value={hostingerMailbox} onChange={e=>setHostingerMailbox(e.target.value)} placeholder="sales@yourdomain.com" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender name <span className="font-medium text-[#9598A2]">(optional)</span></span><input value={hostingerDisplayName} onChange={e=>setHostingerDisplayName(e.target.value)} placeholder="Your name or company" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label></div><div className="mt-4 flex flex-col gap-3 rounded-[10px] bg-[#F7F6FC] px-4 py-3 sm:flex-row sm:items-center sm:justify-between"><div className="text-xs leading-5 text-[#6E717D]">Use a Hostinger token restricted to the mailbox you want to send from.</div><button disabled={!hostingerToken.trim()||connectingHostinger} onClick={()=>void handleConnectHostinger()} className="focus-ring shrink-0 rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40">{connectingHostinger?'Connecting…':'Connect Hostinger'}</button></div></section>
      <section className="card-surface rounded-[14px] p-6"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Optional sender</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Gmail</h2><p className="mt-1 max-w-2xl text-sm text-[#777A87]">Gmail OAuth remains available if you configure it later.</p></div><button disabled={connectingGmail} onClick={handleConnectGmail} className="focus-ring rounded-[9px] border border-[#DDDDE4] bg-white px-4 py-2.5 text-sm font-bold text-[#4B4F5E]"><Icon name="mail" className="mr-2 inline h-4 w-4" />{connectingGmail?'Opening Google…':'Connect Gmail'}</button></div></section>
      <section className="card-surface rounded-[14px] p-6"><div className="text-sm font-bold text-[#343741]">Connected senders</div><div className="mt-4 divide-y divide-[#ECECF1] rounded-[10px] border border-[#E5E5EA]">{senders.map(s=><div key={s.id} className="flex items-center justify-between gap-3 p-4"><div><div className="flex items-center gap-2"><div className="font-bold text-[#2D3038]">{s.email}</div><span className="rounded-md bg-[#F2F1F6] px-2 py-1 text-[10px] font-extrabold uppercase tracking-[0.05em] text-[#6C6F79]">{s.provider === 'hostinger' ? 'Hostinger' : 'Gmail'}</span></div><div className="mt-1 text-xs text-[#858894]">{s.display_name || s.email} · {s.status}</div>{s.last_error&&<div className="mt-1 text-xs text-[#9D3D36]">{s.last_error}</div>}</div><button onClick={async()=>{const token=await getToken();await disconnectSender(token,s.id);await load(false)}} className="rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#555966]">Disconnect</button></div>)}{!senders.length&&<div className="p-6 text-center text-sm text-[#858894]">No sender connected yet.</div>}</div></section>
      <section className="card-surface rounded-[14px] p-6"><div className="text-sm font-bold text-[#343741]">Manual suppression</div><p className="mt-1 text-xs text-[#858894]">Add an address that must never be included in future campaign creation or Quick Send.</p><div className="mt-3 flex flex-col gap-2 sm:flex-row"><input value={suppressAddress} onChange={e=>setSuppressAddress(e.target.value)} placeholder="name@example.com" className="focus-ring h-10 flex-1 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm" /><button disabled={!suppressAddress.trim()} onClick={async()=>{try{const token=await getToken();await suppressEmail(token,suppressAddress.trim());setSuppressAddress('');setNotice('Email added to suppression list.')}catch(next){setError(next instanceof ApiRequestError?next.message:'Could not suppress email.')}}} className="focus-ring rounded-[9px] border border-[#D9D4F7] bg-white px-4 py-2 text-sm font-bold text-[#6B54D7] disabled:opacity-40">Suppress email</button></div></section>
    </div>}
  </div>
}
