import { useEffect, useMemo, useState } from 'react'
import { Icon } from '../components/Icon'
import {
  ApiRequestError, campaignAction, connectHostingerSender, createCampaign, deleteTemplate, disconnectSender,
  getCampaigns, getGmailAuthorizeUrl, getSenders, getTemplates, saveTemplate, suppressEmail,
  type Campaign, type CampaignCreateResult, type EmailTemplate, type SenderConnection,
} from '../lib/api'

type Props = {
  getToken: () => Promise<string>
  initialLeadIds: string[]
  onClearInitialLeadIds: () => void
  onOpenLeads: () => void
}

type Tab = 'campaigns' | 'templates' | 'senders'

const sampleTemplate = {
  name: 'Simple introduction',
  category: 'General',
  subject: 'Quick question for {{company_name}}',
  body: `Hi {{first_name}},\n\nI came across {{company_name}} while researching businesses in {{location}}.\n\nI wanted to reach out with a quick idea that may be useful for your team.\n\nWould you be open to a short conversation?\n\nIf you'd rather not receive messages from me, reply unsubscribe.\n\nBest,\n{{sender_name}}`,
}

export function OutreachPage({ getToken, initialLeadIds, onClearInitialLeadIds, onOpenLeads }: Props) {
  const [tab, setTab] = useState<Tab>('campaigns')
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [senders, setSenders] = useState<SenderConnection[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
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
  const [startHour, setStartHour] = useState(9)
  const [endHour, setEndHour] = useState(17)
  const [intervalSeconds, setIntervalSeconds] = useState(60)
  const [suppressAddress, setSuppressAddress] = useState('')
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

  async function load() {
    setLoading(true); setError(null)
    try {
      const token = await getToken()
      const [t, s, c] = await Promise.all([getTemplates(token), getSenders(token), getCampaigns(token)])
      setTemplates(t); setSenders(s); setCampaigns(c)
      if (!templateId && t[0]) setTemplateId(t[0].id)
      if (!senderId && s[0]) setSenderId(s[0].id)
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not load outreach.')
    } finally { setLoading(false) }
  }

  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const gmail = params.get('gmail')
    if (gmail === 'connected') {
      setNotice('Gmail sender connected successfully.')
      setTab('senders')
      params.delete('gmail'); window.history.replaceState({}, '', `${window.location.pathname}${params.toString() ? `?${params}` : ''}`)
      void load()
    } else if (gmail === 'error') {
      setError('Gmail connection did not complete. Check the OAuth configuration and try again.')
      setTab('senders')
      params.delete('gmail'); window.history.replaceState({}, '', window.location.pathname)
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
      setTemplateForm(sampleTemplate); setEditingTemplate(undefined); setNotice('Template saved.'); await load()
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
        api_token: hostingerToken.trim(),
        mailbox_email: hostingerMailbox.trim() || undefined,
        display_name: hostingerDisplayName.trim() || undefined,
      })
      setHostingerToken(''); setHostingerMailbox(''); setHostingerDisplayName('')
      setNotice(`Hostinger mailbox ${sender.email} connected successfully.`); await load(); setSenderId(sender.id)
    } catch (next) {
      setError(next instanceof ApiRequestError ? next.message : 'Could not connect Hostinger Mail.')
    } finally { setConnectingHostinger(false) }
  }

  async function handleCreateCampaign() {
    if (!initialLeadIds.length) return
    setCreatingCampaign(true); setError(null); setNotice(null)
    try {
      const token = await getToken()
      const result = await createCampaign(token, {
        name: campaignName, lead_ids: initialLeadIds, template_id: templateId, sender_id: senderId,
        daily_limit: dailyLimit, send_start_hour: startHour, send_end_hour: endHour,
        timezone, min_interval_seconds: intervalSeconds,
      })
      setCampaignResult(result); setNotice('Draft created. Review the preview before approving.'); onClearInitialLeadIds(); await load()
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not create campaign.') }
    finally { setCreatingCampaign(false) }
  }

  async function act(campaignId: string, action: 'approve'|'pause'|'resume'|'cancel') {
    setError(null); setNotice(null)
    try {
      const token = await getToken(); await campaignAction(token, campaignId, action)
      setNotice(action === 'approve' ? 'Campaign approved and queued for sending.' : `Campaign ${action}d.`)
      setCampaignResult(null); await load()
    } catch (next) { setError(next instanceof ApiRequestError ? next.message : 'Could not update campaign.') }
  }

  return <div className="space-y-5">
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[
        ['Campaigns', totals.campaigns, 'Saved outreach'], ['Recipients', totals.recipients, 'Across campaigns'],
        ['Sent', totals.sent, 'Accepted by sender API'], ['Failed', totals.failed, 'Needs review'],
      ].map(([label,value,helper]) => <div key={String(label)} className="card-surface rounded-[12px] px-5 py-4">
        <div className="text-xs font-bold uppercase tracking-[0.07em] text-[#858894]">{label}</div>
        <div className="mt-1 font-display text-2xl font-bold text-[#1F2128]">{value}</div><div className="mt-1 text-xs text-[#8A8D97]">{helper}</div>
      </div>)}
    </section>

    {notice && <div className="rounded-[10px] border border-[#DDE9B9] bg-[#F7FBEA] px-4 py-3 text-sm font-medium text-[#59731C]">{notice}</div>}
    {error && <div className="rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>}

    <section className="card-surface rounded-[14px] p-2">
      <div className="flex flex-wrap gap-1">
        {(['campaigns','templates','senders'] as Tab[]).map((item) => <button key={item} onClick={() => setTab(item)} className={`focus-ring rounded-[9px] px-4 py-2.5 text-sm font-bold capitalize ${tab===item?'bg-[#14151C] text-white':'text-[#666A76] hover:bg-[#F4F3F8]'}`}>{item}</button>)}
      </div>
    </section>

    {tab === 'campaigns' && <div className="space-y-5">
      <section className="card-surface rounded-[14px] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Create campaign</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Send to selected leads</h2><p className="mt-1 text-sm text-[#777A87]">Messages remain drafts until you explicitly approve the campaign.</p></div>
          {!initialLeadIds.length && <button onClick={onOpenLeads} className="focus-ring rounded-[9px] border border-[#DCDDE5] bg-white px-4 py-2.5 text-sm font-bold text-[#4B4F5E] hover:bg-[#F8F8FA]">Select leads</button>}
        </div>
        {initialLeadIds.length > 0 && <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Campaign name</span><input value={campaignName} onChange={e=>setCampaignName(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Template</span><select value={templateId} onChange={e=>setTemplateId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose template</option>{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender</span><select value={senderId} onChange={e=>setSenderId(e.target.value)} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value="">Choose sender</option>{senders.map(s=><option key={s.id} value={s.id}>{s.email} · {s.provider === 'hostinger' ? 'Hostinger' : 'Gmail'}</option>)}</select></label>
          <div className="grid grid-cols-2 gap-3"><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Daily limit</span><input type="number" min={1} max={200} value={dailyLimit} onChange={e=>setDailyLimit(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Min interval</span><select value={intervalSeconds} onChange={e=>setIntervalSeconds(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm"><option value={60}>60 sec</option><option value={90}>90 sec</option><option value={120}>2 min</option><option value={180}>3 min</option></select></label></div>
          <div className="grid grid-cols-2 gap-3"><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Start hour</span><input type="number" min={0} max={23} value={startHour} onChange={e=>setStartHour(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label><label><span className="mb-1.5 block text-xs font-bold text-[#555966]">End hour</span><input type="number" min={1} max={24} value={endHour} onChange={e=>setEndHour(Number(e.target.value))} className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label></div>
          <div className="lg:col-span-2 flex items-center justify-between rounded-[10px] bg-[#F6F5FA] px-4 py-3"><div><div className="text-sm font-bold text-[#343741]">{initialLeadIds.length} selected lead{initialLeadIds.length===1?'':'s'}</div><div className="text-xs text-[#858894]">Timezone: {timezone}. Missing/suppressed addresses are skipped automatically.</div></div><button disabled={!templateId||!senderId||creatingCampaign} onClick={handleCreateCampaign} className="focus-ring rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#6D53F0] disabled:opacity-40">{creatingCampaign?'Preparing…':'Preview campaign'}</button></div>
        </div>}
      </section>

      {campaignResult && <section className="rounded-[14px] border border-[#DCD7FF] bg-[#FBFAFF] p-6"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Approval required</p><h3 className="mt-1 font-display text-lg font-bold text-[#22242B]">Review before sending</h3><p className="mt-1 text-sm text-[#777A87]">{campaignResult.campaign.recipient_count} recipients · {campaignResult.suppressed_count} suppressed · {campaignResult.missing_email_count} missing email</p></div><button onClick={()=>act(campaignResult.campaign.id,'approve')} className="focus-ring rounded-[9px] bg-[#14151C] px-4 py-2.5 text-sm font-bold text-white">Approve & queue</button></div><div className="mt-4 grid gap-3 xl:grid-cols-3">{campaignResult.preview.map(item=><div key={item.lead_id} className="rounded-[10px] border border-[#E4E2EF] bg-white p-4"><div className="text-xs font-bold text-[#7A7D88]">To: {item.to_email}</div><div className="mt-2 text-sm font-bold text-[#2C2F37]">{item.subject}</div><pre className="mt-2 whitespace-pre-wrap font-sans text-xs leading-5 text-[#686B75]">{item.body}</pre></div>)}</div></section>}

      <section className="card-surface overflow-hidden rounded-[14px]"><div className="border-b border-[#E8E8EE] px-6 py-5"><h2 className="font-display text-xl font-bold text-[#1C1E25]">Campaigns</h2><p className="mt-1 text-sm text-[#777A87]">Pause or cancel at any time. The worker respects your sending window and daily limit.</p></div>{loading?<div className="p-6 text-sm text-[#777A87]">Loading…</div>:campaigns.length===0?<div className="p-8 text-center text-sm text-[#858894]">No campaigns yet.</div>:<div className="divide-y divide-[#ECECF1]">{campaigns.map(c=><div key={c.id} className="flex flex-col gap-3 px-6 py-4 lg:flex-row lg:items-center lg:justify-between"><div><div className="flex items-center gap-2"><span className="font-bold text-[#2D3038]">{c.name}</span><span className="rounded-md bg-[#F3F2F7] px-2 py-1 text-[10px] font-extrabold uppercase text-[#6D6F79]">{c.status}</span></div><div className="mt-1 text-xs text-[#858894]">{c.sender_email || 'Sender'} · {c.sent_count}/{c.recipient_count} sent · {c.failed_count} failed</div></div><div className="flex gap-2">{c.status==='draft'&&<button onClick={()=>act(c.id,'approve')} className="rounded-[8px] bg-[#7B61FF] px-3 py-2 text-xs font-bold text-white">Approve</button>}{c.status==='sending'&&<button onClick={()=>act(c.id,'pause')} className="rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#555966]">Pause</button>}{c.status==='paused'&&<button onClick={()=>act(c.id,'resume')} className="rounded-[8px] bg-[#14151C] px-3 py-2 text-xs font-bold text-white">Resume</button>}{!['completed','cancelled'].includes(c.status)&&<button onClick={()=>act(c.id,'cancel')} className="rounded-[8px] border border-[#F0CBC8] px-3 py-2 text-xs font-bold text-[#9D3D36]">Cancel</button>}</div></div>)}</div>}</section>
    </div>}

    {tab === 'templates' && <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]"><section className="card-surface rounded-[14px] p-6"><h2 className="font-display text-xl font-bold text-[#22242B]">Email template</h2><p className="mt-1 text-sm text-[#777A87]">Supported: {'{{first_name}}'}, {'{{company_name}}'}, {'{{job_title}}'}, {'{{location}}'}, {'{{website}}'}, {'{{sender_name}}'}.</p><div className="mt-5 space-y-4"><input value={templateForm.name} onChange={e=>setTemplateForm({...templateForm,name:e.target.value})} placeholder="Template name" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><input value={templateForm.category} onChange={e=>setTemplateForm({...templateForm,category:e.target.value})} placeholder="Category" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><input value={templateForm.subject} onChange={e=>setTemplateForm({...templateForm,subject:e.target.value})} placeholder="Subject" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><textarea value={templateForm.body} onChange={e=>setTemplateForm({...templateForm,body:e.target.value})} rows={11} className="focus-ring w-full rounded-[9px] border border-[#DDDDE4] p-3 text-sm" /><button disabled={savingTemplate} onClick={handleSaveTemplate} className="focus-ring rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white">{savingTemplate?'Saving…':editingTemplate?'Update template':'Save template'}</button></div></section><section className="card-surface overflow-hidden rounded-[14px]"><div className="border-b border-[#E8E8EE] px-6 py-5"><h2 className="font-display text-xl font-bold text-[#22242B]">Saved templates</h2></div><div className="divide-y divide-[#ECECF1]">{templates.map(t=><div key={t.id} className="p-5"><div className="flex items-start justify-between gap-3"><div><div className="font-bold text-[#2D3038]">{t.name}</div><div className="mt-1 text-xs text-[#858894]">{t.category} · {t.subject}</div></div><div className="flex gap-2"><button onClick={()=>{setEditingTemplate(t.id);setTemplateForm({name:t.name,category:t.category,subject:t.subject,body:t.body})}} className="rounded-md border border-[#DDDDE4] px-2.5 py-1.5 text-xs font-bold">Edit</button><button onClick={async()=>{const token=await getToken();await deleteTemplate(token,t.id);await load()}} className="rounded-md border border-[#F0CBC8] px-2.5 py-1.5 text-xs font-bold text-[#9D3D36]">Delete</button></div></div></div>)}{!templates.length&&<div className="p-8 text-center text-sm text-[#858894]">Create your first template.</div>}</div></section></div>}

    {tab === 'senders' && <div className="space-y-5">
      <section className="card-surface rounded-[14px] p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Recommended sender</p>
          <h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Hostinger Mail</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-[#777A87]">Paste the Agentic Mail API token you created in Hostinger. The backend validates the token, discovers its allowed mailbox, encrypts the token, and never returns the plaintext value to the browser.</p>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <label className="lg:col-span-2"><span className="mb-1.5 block text-xs font-bold text-[#555966]">Hostinger API token</span><input type="password" autoComplete="off" value={hostingerToken} onChange={e=>setHostingerToken(e.target.value)} placeholder="Paste token once" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Mailbox email <span className="font-medium text-[#9598A2]">(optional)</span></span><input value={hostingerMailbox} onChange={e=>setHostingerMailbox(e.target.value)} placeholder="sales@yourdomain.com" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /><span className="mt-1.5 block text-[11px] leading-4 text-[#8A8D97]">Leave blank when the token has access to only one mailbox.</span></label>
          <label><span className="mb-1.5 block text-xs font-bold text-[#555966]">Sender name <span className="font-medium text-[#9598A2]">(optional)</span></span><input value={hostingerDisplayName} onChange={e=>setHostingerDisplayName(e.target.value)} placeholder="Your name or company" className="focus-ring h-11 w-full rounded-[9px] border border-[#DDDDE4] px-3 text-sm" /></label>
        </div>
        <div className="mt-4 flex flex-col gap-3 rounded-[10px] bg-[#F7F6FC] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs leading-5 text-[#6E717D]">Use a Hostinger token restricted to the mailbox you want to send from. Campaign approval and daily limits still apply.</div>
          <button disabled={!hostingerToken.trim() || connectingHostinger} onClick={()=>void handleConnectHostinger()} className="focus-ring shrink-0 rounded-[9px] bg-[#7B61FF] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#6D53F0] disabled:opacity-40">{connectingHostinger?'Connecting…':'Connect Hostinger'}</button>
        </div>
      </section>

      <section className="card-surface rounded-[14px] p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div><p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Optional sender</p><h2 className="mt-1 font-display text-xl font-bold text-[#22242B]">Gmail</h2><p className="mt-1 max-w-2xl text-sm text-[#777A87]">Gmail OAuth remains available if you configure it later. You do not need it to use Hostinger campaigns.</p></div>
          <button disabled={connectingGmail} onClick={handleConnectGmail} className="focus-ring rounded-[9px] border border-[#DDDDE4] bg-white px-4 py-2.5 text-sm font-bold text-[#4B4F5E]"><Icon name="mail" className="mr-2 inline h-4 w-4" />{connectingGmail?'Opening Google…':'Connect Gmail'}</button>
        </div>
      </section>

      <section className="card-surface rounded-[14px] p-6">
        <div className="text-sm font-bold text-[#343741]">Connected senders</div>
        <div className="mt-4 divide-y divide-[#ECECF1] rounded-[10px] border border-[#E5E5EA]">{senders.map(s=><div key={s.id} className="flex items-center justify-between gap-3 p-4"><div><div className="flex items-center gap-2"><div className="font-bold text-[#2D3038]">{s.email}</div><span className="rounded-md bg-[#F2F1F6] px-2 py-1 text-[10px] font-extrabold uppercase tracking-[0.05em] text-[#6C6F79]">{s.provider === 'hostinger' ? 'Hostinger' : 'Gmail'}</span></div><div className="mt-1 text-xs text-[#858894]">{s.display_name || s.email} · {s.status}</div>{s.last_error&&<div className="mt-1 text-xs text-[#9D3D36]">{s.last_error}</div>}</div><button onClick={async()=>{const token=await getToken();await disconnectSender(token,s.id);await load()}} className="rounded-[8px] border border-[#DDDDE4] px-3 py-2 text-xs font-bold text-[#555966]">Disconnect</button></div>)}{!senders.length&&<div className="p-6 text-center text-sm text-[#858894]">No sender connected yet.</div>}</div>
      </section>

      <section className="card-surface rounded-[14px] p-6">
        <div className="text-sm font-bold text-[#343741]">Manual suppression</div>
        <p className="mt-1 text-xs text-[#858894]">Add an address that must never be included in future campaign creation.</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row"><input value={suppressAddress} onChange={e=>setSuppressAddress(e.target.value)} placeholder="name@example.com" className="focus-ring h-10 flex-1 rounded-[9px] border border-[#DDDDE4] bg-white px-3 text-sm" /><button disabled={!suppressAddress.trim()} onClick={async()=>{try{const token=await getToken();await suppressEmail(token,suppressAddress.trim());setSuppressAddress('');setNotice('Email added to suppression list.')}catch(next){setError(next instanceof ApiRequestError?next.message:'Could not suppress email.')}}} className="focus-ring rounded-[9px] border border-[#D9D4F7] bg-white px-4 py-2 text-sm font-bold text-[#6B54D7] disabled:opacity-40">Suppress email</button></div>
      </section>
    </div>}
  </div>
}
