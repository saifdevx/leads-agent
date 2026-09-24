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
  getCampaignDetail,
  getGmailAuthorizeUrl,
  getOutreachSnapshot,
  quickSend,
  retryCampaignMessage,
  saveTemplate,
  setupHostingerWebhook,
  suppressEmail,
  syncSenderReplies,
  type Campaign,
  type CampaignCreateResult,
  type CampaignDetail,
  type EmailTemplate,
  type OutreachReply,
  type SenderConnection,
} from '../lib/api'

type Props = {
  getToken: () => Promise<string>
  initialLeadIds: string[]
  onClearInitialLeadIds: () => void
  onOpenLeads: () => void
}

type Tab = 'campaigns' | 'inbox' | 'quick' | 'templates' | 'senders'

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

function replyClasses(classification: string) {
  if (classification === 'interested') return 'bg-[#F0F8DC] text-[#688328]'
  if (classification === 'unsubscribe') return 'bg-[#FFF0EE] text-[#9D3D36]'
  if (classification === 'not_interested') return 'bg-[#F3F3F5] text-[#737680]'
  if (classification === 'out_of_office') return 'bg-[#FFF7E8] text-[#9B6A20]'
  return 'bg-[#F0EDFF] text-[#6753C8]'
}

function scheduleLabel(campaign: Campaign) {
  if (campaign.send_start_hour === 0 && campaign.send_end_hour === 24) return 'Send anytime'
  const start = String(campaign.send_start_hour).padStart(2, '0')
  const end = String(campaign.send_end_hour).padStart(2, '0')
  return `${start}:00–${end}:00 ${campaign.timezone}`
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function OutreachPage({ getToken, initialLeadIds, onClearInitialLeadIds, onOpenLeads }: Props) {
  const [tab, setTab] = useState<Tab>('campaigns')
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [senders, setSenders] = useState<SenderConnection[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [replies, setReplies] = useState<OutreachReply[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)
  const [busyCampaignId, setBusyCampaignId] = useState<string | null>(null)
  const [syncingReplies, setSyncingReplies] = useState(false)
  const [webhookBusyId, setWebhookBusyId] = useState<string | null>(null)

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
  const [stopOnReply, setStopOnReply] = useState(true)
  const [followUp1, setFollowUp1] = useState(false)
  const [followUp1Template, setFollowUp1Template] = useState('')
  const [followUp1Delay, setFollowUp1Delay] = useState(72)
  const [followUp2, setFollowUp2] = useState(false)
  const [followUp2Template, setFollowUp2Template] = useState('')
  const [followUp2Delay, setFollowUp2Delay] = useState(96)
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

  const [quickSenderId, setQuickSenderId] = useState('')
  const [quickTo, setQuickTo] = useState('')
  const [quickSubject, setQuickSubject] = useState('Test from Lead Gen')
  const [quickBody, setQuickBody] = useState('This is a test message from Lead Gen.')
  const [quickSending, setQuickSending] = useState(false)
  const [suppressAddress, setSuppressAddress] = useState('')

  const [detail, setDetail] = useState<CampaignDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  async function load(showLoader = true, force = false) {
    if (showLoader) setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const snapshot = await getOutreachSnapshot(token, force)
      setTemplates(snapshot.templates)
      setSenders(snapshot.senders)
      setCampaigns(snapshot.campaigns)
      setReplies(snapshot.replies)
      setTemplateId((current) => current || snapshot.templates[0]?.id || '')
      setFollowUp1Template((current) => current || snapshot.templates[0]?.id || '')
      setFollowUp2Template((current) => current || snapshot.templates[0]?.id || '')
      setSenderId((current) => current || snapshot.senders[0]?.id || '')
      setQuickSenderId((current) => current || snapshot.senders[0]?.id || '')
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
    const timer = window.setInterval(() => { void load(false, true) }, 10000)
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
      void load(false, true)
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
    replies: acc.replies + campaign.replied_count,
    interested: acc.interested + campaign.interested_count,
    failed: acc.failed + campaign.failed_count,
  }), { campaigns: 0, recipients: 0, sent: 0, replies: 0, interested: 0, failed: 0 }), [campaigns])

  async function handleSaveTemplate() {
    setSavingTemplate(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      const saved = await saveTemplate(token, templateForm, editingTemplate)
      setTemplates((current) => editingTemplate ? current.map((item) => item.id === saved.id ? saved : item) : [saved, ...current])
      setTemplateForm(sampleTemplate); setEditingTemplate(undefined); setNotice('Template saved.')
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

  async function enableLiveReplies(sender: SenderConnection) {
    setWebhookBusyId(sender.id); setError(null); setNotice(null)
    try {
      const token = await getToken()
      const result = await setupHostingerWebhook(token, sender.id)
      setSenders(current => current.map(item => item.id === sender.id ? { ...item, webhook_status: 'active', webhook_url: result.url } : item))
      setNotice('Live Hostinger replies enabled for this sender.')
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not enable live replies.')
    } finally { setWebhookBusyId(null) }
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
      setSenders((current) => [sender, ...current.filter((item) => item.id !== sender.id)])
      setNotice(`Hostinger mailbox ${sender.email} connected successfully.`)
      setSenderId(sender.id); setQuickSenderId(sender.id)
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not connect Hostinger Mail.') }
    finally { setConnectingHostinger(false) }
  }

  async function handleCreateCampaign() {
    if (!initialLeadIds.length) return
    if (useSendingWindow && startHour === endHour) {
      setError('Choose different start and end hours, or turn the sending window off.')
      return
    }
    const followUps: { template_id: string; delay_hours: number }[] = []
    if (followUp1 && followUp1Template) followUps.push({ template_id: followUp1Template, delay_hours: followUp1Delay })
    if (followUp2 && followUp2Template) followUps.push({ template_id: followUp2Template, delay_hours: followUp2Delay })
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
        stop_on_reply: stopOnReply,
        follow_ups: followUps,
      })
      setCampaignResult(result)
      setCampaigns((current) => [result.campaign, ...current])
      setNotice('Draft created. Review the preview before approving.'); onClearInitialLeadIds()
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
    setError(null); setNotice(null); setBusyCampaignId(campaignId)
    const previous = campaigns
    const optimisticStatus = action === 'approve' || action === 'resume' ? 'sending' : action === 'pause' ? 'paused' : 'cancelled'
    setCampaigns((current) => current.map((item) => item.id === campaignId ? { ...item, status: optimisticStatus, updated_at: new Date().toISOString() } : item))
    try {
      const token = await getToken()
      const updated = await campaignAction(token, campaignId, action)
      setCampaigns((current) => current.map((item) => item.id === campaignId ? updated : item))
      setNotice(action === 'approve' ? 'Campaign approved and queued for sending.' : `Campaign ${action}d.`)
      setCampaignResult(null)
    } catch (next) {
      setCampaigns(previous)
      setError(next instanceof ApiRequestError ? next.message : 'Could not update campaign.')
    } finally { setBusyCampaignId(null) }
  }

  async function removeCampaign(campaignId: string) {
    if (!window.confirm('Delete this campaign and its message records? This cannot be undone.')) return
    setError(null); setNotice(null); setBusyCampaignId(campaignId)
    const previous = campaigns
    setCampaigns((current) => current.filter((item) => item.id !== campaignId))
    try {
      const token = await getToken(); await deleteCampaign(token, campaignId); setNotice('Campaign deleted.')
      if (detail?.campaign.id === campaignId) setDetail(null)
    } catch (next) {
      setCampaigns(previous)
      setError(next instanceof ApiRequestError ? next.message : 'Could not delete campaign.')
    } finally { setBusyCampaignId(null) }
  }

  async function openDetail(campaignId: string) {
    setDetailLoading(true); setError(null)
    try {
      const token = await getToken()
      setDetail(await getCampaignDetail(token, campaignId, true))
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not load campaign details.')
    } finally { setDetailLoading(false) }
  }

  async function syncReplies() {
    const hostinger = senders.filter((sender) => sender.provider === 'hostinger')
    if (!hostinger.length) { setError('Connect a Hostinger sender before syncing replies.'); return }
    setSyncingReplies(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      let checked = 0; let found = 0
      for (const sender of hostinger) {
        const result = await syncSenderReplies(token, sender.id)
        checked += result.checked_count; found += result.new_replies
      }
      setNotice(`Reply sync checked ${checked} inbox message${checked === 1 ? '' : 's'} and found ${found} new campaign repl${found === 1 ? 'y' : 'ies'}.`)
      await load(false, true)
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not sync replies.')
    } finally { setSyncingReplies(false) }
  }

  async function retryMessage(campaignId: string, messageId: string) {
    try {
      const token = await getToken()
      await retryCampaignMessage(token, campaignId, messageId)
      setNotice('Failed email re-queued.')
      setDetail(await getCampaignDetail(token, campaignId, true))
      await load(false, true)
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not retry this email.')
    }
  }

  if (loading) return <div className="card-surface animate-soft-in rounded-[14px] p-8 text-sm text-[#777A87]">Loading outreach…</div>

  return <div className="space-y-5 animate-soft-in">
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {[
        ['Campaigns', totals.campaigns, 'Saved outreach'], ['Sent', totals.sent, 'Messages delivered'],
        ['Replies', totals.replies, 'Unique recipients'], ['Interested', totals.interested, 'Positive replies'],
        ['Failed', totals.failed, 'Needs review'],
      ].map(([label, value, helper]) => <div key={String(label)} className="card-surface motion-card rounded-[12px] px-5 py-4">
        <div className="text-xs font-bold uppercase tracking-[0.07em] text-[#858894]">{label}</div>
        <div className="mt-1 font-display text-2xl font-bold text-[#1F2128]">{value}</div>
        <div className="mt-1 text-xs text-[#8A8D97]">{helper}</div>
      </div>)}
    </section>

    {notice && <div className="toast-enter rounded-[10px] border border-[#DDE9B9] bg-[#F7FBEA] px-4 py-3 text-sm font-medium text-[#59731C]">{notice}</div>}
    {error && <div className="toast-enter rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>}

    <div className="flex flex-col gap-3 rounded-[14px] border border-[#E6E6EC] bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap gap-1.5">
        {(['campaigns','inbox','quick','templates','senders'] as Tab[]).map((item) => <button key={item} onClick={()=>setTab(item)} className={`button-pop rounded-[8px] px-3.5 py-2 text-sm font-bold capitalize ${tab===item?'bg-[#14151C] text-white':'text-[#6E717D] hover:bg-[#F4F4F7]'}`}>{item === 'quick' ? 'Quick Send' : item}</button>)}
      </div>
      <div className="flex items-center gap-2 text-xs text-[#858894]">
        {lastRefreshed && <span>Updated {lastRefreshed.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</span>}
        <button onClick={()=>void load(false,true)} className="button-pop rounded-[8px] border border-[#DDDDE4] px-3 py-2 font-bold text-[#555966]">Refresh</button>
      </div>
    </div>

    {tab === 'campaigns' && <div className="space-y-5">
      {initialLeadIds.length > 0 ? <section className="card-surface rounded-[14px] p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Create campaign</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Send to selected leads</h2><p className="mt-1 text-sm text-[#777A87]">Messages remain drafts until you explicitly approve the campaign.</p></div><span className="rounded-full bg-[#F0EDFF] px-3 py-1.5 text-xs font-extrabold text-[#6753C8]">{initialLeadIds.length} selected</span></div>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Campaign name</span><input value={campaignName} onChange={e=>setCampaignName(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Initial template</span><select value={templateId} onChange={e=>setTemplateId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose template</option>{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender</span><select value={senderId} onChange={e=>setSenderId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose sender</option>{senders.map(s=><option key={s.id} value={s.id}>{s.email} · {s.provider}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Daily limit</span><input type="number" min={1} max={200} value={dailyLimit} onChange={e=>setDailyLimit(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Interval</span><select value={intervalSeconds} onChange={e=>setIntervalSeconds(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value={20}>20 sec</option><option value={30}>30 sec</option><option value={45}>45 sec</option><option value={60}>60 sec</option><option value={90}>90 sec</option><option value={120}>2 min</option></select></label>
          <label className="flex items-center gap-3 rounded-[10px] border border-[#E4E2EF] bg-[#FAF9FF] px-4 py-3"><input type="checkbox" checked={stopOnReply} onChange={e=>setStopOnReply(e.target.checked)} className="h-4 w-4 accent-[#7B61FF]"/><span><span className="block text-sm font-bold text-[#343741]">Stop on reply</span><span className="block text-xs text-[#858894]">Recommended. Future follow-ups are cancelled immediately.</span></span></label>
        </div>

        <div className="mt-4 rounded-[12px] border border-[#E6E3F4] bg-[#FBFAFF] p-4">
          <div className="text-sm font-bold text-[#343741]">Follow-up sequence <span className="font-medium text-[#858894]">(optional)</span></div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <div className="rounded-[10px] bg-white p-3 ring-1 ring-[#E7E5F0]"><label className="flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={followUp1} onChange={e=>setFollowUp1(e.target.checked)} className="accent-[#7B61FF]"/> Follow-up 1</label>{followUp1&&<div className="mt-3 grid gap-2 sm:grid-cols-[1fr_130px]"><select value={followUp1Template} onChange={e=>setFollowUp1Template(e.target.value)} className="h-10 rounded-[8px] border border-[#DDDDE4] bg-white px-2 text-sm">{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select><select value={followUp1Delay} onChange={e=>setFollowUp1Delay(Number(e.target.value))} className="h-10 rounded-[8px] border border-[#DDDDE4] bg-white px-2 text-sm"><option value={24}>1 day</option><option value={48}>2 days</option><option value={72}>3 days</option><option value={120}>5 days</option><option value={168}>7 days</option></select></div>}</div>
            <div className="rounded-[10px] bg-white p-3 ring-1 ring-[#E7E5F0]"><label className="flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={followUp2} onChange={e=>setFollowUp2(e.target.checked)} disabled={!followUp1} className="accent-[#7B61FF]"/> Follow-up 2</label>{followUp2&&followUp1&&<div className="mt-3 grid gap-2 sm:grid-cols-[1fr_130px]"><select value={followUp2Template} onChange={e=>setFollowUp2Template(e.target.value)} className="h-10 rounded-[8px] border border-[#DDDDE4] bg-white px-2 text-sm">{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select><select value={followUp2Delay} onChange={e=>setFollowUp2Delay(Number(e.target.value))} className="h-10 rounded-[8px] border border-[#DDDDE4] bg-white px-2 text-sm"><option value={48}>2 days after follow-up 1</option><option value={72}>3 days</option><option value={96}>4 days</option><option value={168}>7 days</option></select></div>}</div>
          </div>
        </div>

        <label className="mt-4 flex items-center gap-3"><input type="checkbox" checked={useSendingWindow} onChange={e=>setUseSendingWindow(e.target.checked)} className="h-4 w-4 accent-[#7B61FF]"/><span className="text-sm font-bold text-[#4B4F5E]">Limit sending to certain hours</span></label>
        {useSendingWindow&&<div className="mt-3 grid max-w-lg gap-3 sm:grid-cols-2"><label><span className="mb-1 block text-xs font-bold text-[#666A75]">Start hour</span><input type="number" min={0} max={23} value={startHour} onChange={e=>setStartHour(Number(e.target.value))} className="h-10 w-full rounded-[8px] border border-[#DDDDE4] px-3 text-sm"/></label><label><span className="mb-1 block text-xs font-bold text-[#666A75]">End hour</span><input type="number" min={1} max={24} value={endHour} onChange={e=>setEndHour(Number(e.target.value))} className="h-10 w-full rounded-[8px] border border-[#DDDDE4] px-3 text-sm"/></label></div>}
        <div className="mt-5 flex flex-wrap items-center gap-3"><button disabled={creatingCampaign||!templateId||!senderId} onClick={()=>void handleCreateCampaign()} className="button-pop rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40">{creatingCampaign?'Creating…':'Preview campaign'}</button><button onClick={onOpenLeads} className="button-pop rounded-[9px] border border-[#DDDDE4] px-4 py-2.5 text-sm font-bold text-[#555966]">Back to leads</button></div>
      </section> : <section className="card-surface rounded-[14px] p-6"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-display text-xl font-bold text-[#22242B]">Create campaign</h2><p className="mt-1 text-sm text-[#777A87]">Select leads first, then return here to build an outreach sequence.</p></div><button onClick={onOpenLeads} className="button-pop rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white">Select leads</button></div></section>}

      {campaignResult&&<section className="card-surface rounded-[14px] p-6 ring-2 ring-[#E7E2FF]"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[.08em] text-[#7B61FF]">Review draft</p><h3 className="mt-1 font-display text-xl font-bold">{campaignResult.campaign.name}</h3><p className="mt-1 text-sm text-[#777A87]">{campaignResult.campaign.recipient_count} recipients · approval required before sending.</p></div><button disabled={busyCampaignId===campaignResult.campaign.id} onClick={()=>void act(campaignResult.campaign.id,'approve')} className="button-pop rounded-[9px] bg-[#14151C] px-4 py-2.5 text-sm font-bold text-white">Approve & queue</button></div><div className="mt-4 space-y-3">{campaignResult.preview.map(item=><div key={item.lead_id} className="rounded-[10px] bg-[#F8F8FA] p-4 text-sm"><div className="font-bold">{item.to_email}</div><div className="mt-1 text-[#555966]">{item.subject}</div></div>)}</div></section>}

      <section className="card-surface overflow-hidden rounded-[14px]"><div className="border-b border-[#E8E8EE] px-5 py-5 sm:px-6"><h2 className="font-display text-xl font-bold text-[#22242B]">Campaigns</h2><p className="mt-1 text-sm text-[#777A87]">Pause instantly, inspect recipients, retry safe failures and track replies.</p></div><div className="divide-y divide-[#ECECF1]">{campaigns.map(campaign=>{
        const progress = Math.min(100, Math.round(((campaign.sent_count + campaign.failed_count + campaign.replied_count) / Math.max(campaign.recipient_count,1))*100))
        return <div key={campaign.id} className="motion-row p-5"><div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><div className="font-display text-base font-bold text-[#282A31]">{campaign.name}</div><span className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase ${statusClasses(campaign.status)}`}>{campaign.status}</span></div><div className="mt-1 text-xs text-[#858894]">{campaign.sender_email} · {campaign.sent_count} sent · {campaign.replied_count} replies · {campaign.failed_count} failed · every {campaign.min_interval_seconds}s</div><div className="mt-1 text-xs text-[#9A9CA5]">{scheduleLabel(campaign)}{campaign.stop_on_reply?' · stop on reply':''}</div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#ECECF2]"><div className="progress-smooth h-full rounded-full bg-[#7B61FF]" style={{width:`${progress}%`}} /></div></div><div className="flex flex-wrap gap-2">{campaign.status==='sending'&&<button disabled={busyCampaignId===campaign.id} onClick={()=>void act(campaign.id,'pause')} className="button-pop rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold">Pause</button>}{campaign.status==='paused'&&<button disabled={busyCampaignId===campaign.id} onClick={()=>void act(campaign.id,'resume')} className="button-pop rounded-[8px] border border-[#D9D4F7] bg-[#F7F5FF] px-3 py-2 text-xs font-bold text-[#6B54D7]">Resume</button>}{!['cancelled','completed'].includes(campaign.status)&&<button disabled={busyCampaignId===campaign.id} onClick={()=>void act(campaign.id,'cancel')} className="button-pop rounded-[8px] border border-[#F0CBC8] px-3 py-2 text-xs font-bold text-[#9D3D36]">Cancel</button>}<button onClick={()=>void openDetail(campaign.id)} className="button-pop rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold">Details</button>{campaign.status!=='sending'&&<button disabled={busyCampaignId===campaign.id} onClick={()=>void removeCampaign(campaign.id)} className="button-pop rounded-[8px] px-3 py-2 text-xs font-bold text-[#8A6C69]">Delete</button>}</div></div></div>
      })}{!campaigns.length&&<div className="p-8 text-center text-sm text-[#858894]">No campaigns yet.</div>}</div></section>
    </div>}

    {tab === 'inbox' && <section className="card-surface overflow-hidden rounded-[14px]"><div className="flex flex-col gap-3 border-b border-[#E8E8EE] px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div><h2 className="font-display text-xl font-bold text-[#22242B]">Reply inbox</h2><p className="mt-1 text-sm text-[#777A87]">Replies automatically stop future follow-ups when stop-on-reply is enabled.</p></div><button disabled={syncingReplies} onClick={()=>void syncReplies()} className="button-pop rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">{syncingReplies?'Syncing…':'Sync Hostinger replies'}</button></div><div className="divide-y divide-[#ECECF1]">{replies.map(reply=><div key={reply.id} className="motion-row p-5"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><div className="font-bold text-[#292B32]">{reply.company_name || reply.from_email}</div><span className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase ${replyClasses(reply.classification)}`}>{reply.classification.replaceAll('_',' ')}</span></div><div className="mt-1 text-xs text-[#858894]">{reply.from_email} · {reply.campaign_name || 'Campaign reply'} · {formatDate(reply.received_at)}</div><div className="mt-3 text-sm font-bold text-[#3E414A]">{reply.subject || '(No subject)'}</div><div className="mt-1 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-[#686B75]">{reply.snippet || reply.body_text || 'Reply captured.'}</div></div></div></div>)}{!replies.length&&<div className="p-10 text-center"><div className="text-sm font-bold text-[#4F525C]">No campaign replies yet</div><div className="mt-1 text-xs text-[#8A8D97]">Use “Sync Hostinger replies” while developing locally. Real-time webhooks will be enabled after deployment.</div></div>}</div></section>}

    {tab === 'quick' && <section className="card-surface rounded-[14px] p-6"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Direct test</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Quick Send</h2><p className="mt-1 text-sm text-[#777A87]">One recipient at a time. Useful for sender and template testing.</p></div><div className="mt-5 grid gap-4 lg:grid-cols-2"><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender</span><select value={quickSenderId} onChange={e=>setQuickSenderId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose sender</option>{senders.map(s=><option key={s.id} value={s.id}>{s.email} · {s.provider}</option>)}</select></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Recipient email</span><input type="email" value={quickTo} onChange={e=>setQuickTo(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Subject</span><input value={quickSubject} onChange={e=>setQuickSubject(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Message</span><textarea rows={9} value={quickBody} onChange={e=>setQuickBody(e.target.value)} className="focus-ring w-full rounded-[9px] border border-[#DDDDE4] p-3 text-sm" /></label></div><div className="mt-4 flex justify-end"><button disabled={quickSending||!quickSenderId||!quickTo.trim()||!quickSubject.trim()||!quickBody.trim()} onClick={()=>void handleQuickSend()} className="button-pop rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40">{quickSending?'Sending…':'Send now'}</button></div></section>}

    {tab === 'templates' && <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]"><section className="card-surface rounded-[14px] p-6"><h2 className="font-display text-xl font-bold text-[#22242B]">Email template</h2><p className="mt-1 text-sm text-[#777A87]">Supported: {'{{first_name}}'}, {'{{company_name}}'}, {'{{job_title}}'}, {'{{location}}'}, {'{{website}}'}, {'{{sender_name}}'}.</p><div className="mt-5 space-y-4"><input value={templateForm.name} onChange={e=>setTemplateForm({...templateForm,name:e.target.value})} placeholder="Template name" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><input value={templateForm.category} onChange={e=>setTemplateForm({...templateForm,category:e.target.value})} placeholder="Category" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><input value={templateForm.subject} onChange={e=>setTemplateForm({...templateForm,subject:e.target.value})} placeholder="Subject" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><textarea value={templateForm.body} onChange={e=>setTemplateForm({...templateForm,body:e.target.value})} rows={11} className="focus-ring w-full rounded-[9px] border border-[#DDDDE4] p-3 text-sm" /><button disabled={savingTemplate} onClick={()=>void handleSaveTemplate()} className="button-pop rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white">{savingTemplate?'Saving…':editingTemplate?'Update template':'Save template'}</button></div></section><section className="card-surface overflow-hidden rounded-[14px]"><div className="border-b border-[#E8E8EE] px-6 py-5"><h2 className="font-display text-xl font-bold text-[#22242B]">Saved templates</h2></div><div className="divide-y divide-[#ECECF1]">{templates.map(t=><div key={t.id} className="motion-row p-5"><div className="flex items-start justify-between gap-3"><div><div className="font-bold text-[#2D3038]">{t.name}</div><div className="mt-1 text-xs text-[#858894]">{t.category} · {t.subject}</div></div><div className="flex gap-2"><button onClick={()=>{setEditingTemplate(t.id);setTemplateForm({name:t.name,category:t.category,subject:t.subject,body:t.body})}} className="button-pop rounded-md border border-[#DDDDE4] px-2.5 py-1.5 text-xs font-bold">Edit</button><button onClick={async()=>{const previous=templates;setTemplates(c=>c.filter(x=>x.id!==t.id));try{const token=await getToken();await deleteTemplate(token,t.id)}catch{setTemplates(previous)}}} className="button-pop rounded-md border border-[#F0CBC8] px-2.5 py-1.5 text-xs font-bold text-[#9D3D36]">Delete</button></div></div></div>)}{!templates.length&&<div className="p-8 text-center text-sm text-[#858894]">Create your first template.</div>}</div></section></div>}

    {tab === 'senders' && <div className="space-y-5"><section className="card-surface rounded-[14px] p-6"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Recommended sender</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Hostinger Mail</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-[#777A87]">Connect Agentic Mail once. Reply sync works locally; real-time webhook mode is enabled after deployment.</p></div><div className="mt-5 grid gap-4 lg:grid-cols-2"><label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Hostinger API token</span><input type="password" value={hostingerToken} onChange={e=>setHostingerToken(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Mailbox email <span className="font-medium text-[#9598A2]">(optional)</span></span><input value={hostingerMailbox} onChange={e=>setHostingerMailbox(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender name <span className="font-medium text-[#9598A2]">(optional)</span></span><input value={hostingerDisplayName} onChange={e=>setHostingerDisplayName(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label></div><div className="mt-4 flex justify-end"><button disabled={!hostingerToken.trim()||connectingHostinger} onClick={()=>void handleConnectHostinger()} className="button-pop rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40">{connectingHostinger?'Connecting…':'Connect Hostinger'}</button></div></section><section className="card-surface rounded-[14px] p-6"><div className="text-sm font-bold text-[#343741]">Connected senders</div><div className="mt-4 divide-y divide-[#ECECF1] rounded-[10px] border border-[#E5E5EA]">{senders.map(s=><div key={s.id} className="motion-row flex items-center justify-between gap-3 p-4"><div><div className="flex items-center gap-2"><div className="font-bold text-[#2D3038]">{s.email}</div><span className="rounded-md bg-[#F2F1F6] px-2 py-1 text-[10px] font-extrabold uppercase text-[#6C6F79]">{s.provider}</span></div><div className="mt-1 text-xs text-[#858894]">{s.display_name || s.email} · {s.status}{s.provider==='hostinger' ? ` · replies ${s.webhook_status === 'active' ? 'live' : 'manual'}` : ''}</div></div><div className="flex items-center gap-2">{s.provider==='hostinger'&&s.webhook_status!=='active'&&<button disabled={webhookBusyId===s.id} onClick={()=>void enableLiveReplies(s)} className="button-pop rounded-[8px] border border-[#D9D4F7] px-3 py-2 text-xs font-bold text-[#6B54D7] disabled:opacity-50">{webhookBusyId===s.id?'Enabling…':'Enable live replies'}</button>}<button onClick={async()=>{const previous=senders;setSenders(c=>c.filter(x=>x.id!==s.id));try{const token=await getToken();await disconnectSender(token,s.id)}catch{setSenders(previous)}}} className="button-pop rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#555966]">Disconnect</button></div></div>)}{!senders.length&&<div className="p-6 text-center text-sm text-[#858894]">No sender connected yet.</div>}</div></section><section className="card-surface rounded-[14px] p-6"><div className="text-sm font-bold text-[#343741]">Manual suppression</div><p className="mt-1 text-xs text-[#858894]">Addresses here are blocked from campaigns and Quick Send.</p><div className="mt-3 flex flex-col gap-2 sm:flex-row"><input value={suppressAddress} onChange={e=>setSuppressAddress(e.target.value)} placeholder="name@example.com" className="focus-ring h-10 flex-1 rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><button disabled={!suppressAddress.trim()} onClick={async()=>{try{const token=await getToken();await suppressEmail(token,suppressAddress.trim());setSuppressAddress('');setNotice('Email added to suppression list.')}catch(next){setError(next instanceof ApiRequestError?next.message:'Could not suppress email.')}}} className="button-pop rounded-[9px] border border-[#D9D4F7] bg-white px-4 py-2 text-sm font-bold text-[#6B54D7] disabled:opacity-40">Suppress email</button></div></section></div>}

    {(detailLoading || detail) && <div className="fixed inset-0 z-50 flex justify-end bg-[#14151C]/25 backdrop-blur-[2px]" onClick={()=>!detailLoading&&setDetail(null)}><aside className="drawer-enter h-full w-full max-w-2xl overflow-y-auto bg-white shadow-2xl" onClick={e=>e.stopPropagation()}><div className="sticky top-0 z-10 flex items-center justify-between border-b border-[#E8E8EE] bg-white/95 px-6 py-4 backdrop-blur"><div><div className="text-xs font-bold uppercase tracking-[.08em] text-[#7B61FF]">Campaign details</div><div className="mt-1 font-display text-xl font-bold">{detail?.campaign.name || 'Loading…'}</div></div><button onClick={()=>setDetail(null)} className="button-pop rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold">Close</button></div>{detailLoading&&!detail?<div className="p-8 text-sm text-[#777A87]">Loading details…</div>:detail&&<div className="space-y-6 p-6"><div className="grid gap-3 sm:grid-cols-4">{[['Sent',detail.campaign.sent_count],['Replies',detail.campaign.replied_count],['Interested',detail.campaign.interested_count],['Reply rate',`${detail.reply_rate}%`]].map(([label,value])=><div key={String(label)} className="rounded-[10px] bg-[#F7F7FA] p-3"><div className="text-[10px] font-bold uppercase tracking-[.06em] text-[#8A8D97]">{label}</div><div className="mt-1 font-display text-xl font-bold">{value}</div></div>)}</div><div><h3 className="text-sm font-bold">Sequence</h3><div className="mt-2 flex flex-wrap gap-2">{detail.steps.map(step=><span key={step.id} className="rounded-full bg-[#F0EDFF] px-3 py-1.5 text-xs font-bold text-[#6753C8]">{step.step_number===0?'Initial':`Follow-up ${step.step_number}`} · {step.step_number===0?'now':`${step.delay_hours}h later`}</span>)}</div></div><div><h3 className="text-sm font-bold">Recipients & messages</h3><div className="mt-2 divide-y divide-[#ECECF1] rounded-[10px] border border-[#E5E5EA]">{detail.messages.map(message=><div key={message.id} className="p-3"><div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div><div className="text-sm font-bold">{message.company_name || message.to_email}</div><div className="mt-1 text-xs text-[#858894]">{message.to_email} · {message.message_kind} {message.step_number} · {message.status}</div>{message.last_error&&<div className="mt-1 text-xs text-[#9D3D36]">{message.last_error}</div>}</div>{message.status==='failed'&&<button onClick={()=>void retryMessage(detail.campaign.id,message.id)} className="button-pop rounded-[8px] border border-[#D9D4F7] px-3 py-2 text-xs font-bold text-[#6B54D7]">Retry</button>}</div></div>)}</div></div></div>}</aside></div>}
  </div>
}
