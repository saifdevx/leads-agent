export type HealthResponse = {
  status: 'ok'
  service: string
  version: string
  environment: string
  timestamp: string
  request_id: string
}

export type AuthenticatedUserResponse = {
  uid: string
  email: string | null
  name: string | null
  email_verified: boolean
  sign_in_provider: string | null
  role: 'user' | 'admin' | string
  status: 'active' | 'suspended' | string
}

export type LeadList = {
  id: string
  name: string
  niche: string
  location: string | null
  target_count: number
  status: string
  lead_count: number
  created_at: string
  updated_at: string
}

export type Lead = {
  id: string
  list_id: string
  company_name: string | null
  website: string | null
  domain: string | null
  first_name: string | null
  last_name: string | null
  job_title: string | null
  email: string | null
  email_status: string | null
  phone: string | null
  linkedin_url: string | null
  instagram_url: string | null
  facebook_url: string | null
  city: string | null
  region: string | null
  country: string | null
  source: string | null
  source_url: string | null
  source_query: string | null
  score: number | null
  status: string
  created_at: string
  updated_at: string
}

export type SearchPlan = {
  lead_list: LeadList
  queries: string[]
}

export type ImportResult = {
  extracted_count: number
  added_count: number
  duplicate_count: number
  skipped_count: number
  leads: Lead[]
}

type ErrorPayload = {
  error?: {
    code?: string
    message?: string
    request_id?: string | null
  }
}

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

type CacheEntry = { expiresAt: number; value: unknown }
const responseCache = new Map<string, CacheEntry>()
const inflightCache = new Map<string, Promise<unknown>>()

export function invalidateApiCache(prefix = '') {
  for (const key of responseCache.keys()) {
    const path = key.includes('|') ? key.slice(key.indexOf('|') + 1) : key
    if (!prefix || path.startsWith(prefix)) responseCache.delete(key)
  }
}

async function cachedAuthRequest<T>(path: string, idToken: string, ttlMs = 8000, force = false): Promise<T> {
  const key = `${idToken.slice(-24)}|${path}`
  const cached = responseCache.get(key)
  if (!force && cached && cached.expiresAt > Date.now()) return cached.value as T
  if (!force) {
    const active = inflightCache.get(key)
    if (active) return active as Promise<T>
  }
  const request = authRequest<T>(path, idToken)
    .then((value) => {
      responseCache.set(key, { expiresAt: Date.now() + ttlMs, value })
      return value
    })
    .finally(() => inflightCache.delete(key))
  inflightCache.set(key, request)
  return request
}

export class ApiRequestError extends Error {
  status: number
  requestId?: string | null

  constructor(message: string, status: number, requestId?: string | null) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.requestId = requestId
  }
}

async function readError(response: Response, fallback: string): Promise<ApiRequestError> {
  let payload: ErrorPayload | null = null
  try {
    payload = await response.json() as ErrorPayload
  } catch {
    // The backend may return a non-JSON response during an infrastructure failure.
  }

  return new ApiRequestError(
    payload?.error?.message || fallback,
    response.status,
    payload?.error?.request_id,
  )
}

async function authRequest<T>(path: string, idToken: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  headers.set('Authorization', `Bearer ${idToken}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    throw await readError(response, `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, {
    signal,
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw await readError(response, `Health check failed with status ${response.status}`)
  }

  return response.json() as Promise<HealthResponse>
}

export async function getAuthenticatedUser(idToken: string, signal?: AbortSignal): Promise<AuthenticatedUserResponse> {
  return authRequest<AuthenticatedUserResponse>('/api/v1/auth/me', idToken, { signal })
}

export async function createSearchPlan(
  idToken: string,
  input: { niche: string; location?: string; target_count: number },
): Promise<SearchPlan> {
  return authRequest<SearchPlan>('/api/v1/lead-lists/plan', idToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function importLeadText(
  idToken: string,
  listId: string,
  input: { raw_text: string; source_query?: string },
): Promise<ImportResult> {
  return authRequest<ImportResult>(`/api/v1/lead-lists/${encodeURIComponent(listId)}/import-text`, idToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function getLeadLists(idToken: string, force = false): Promise<LeadList[]> {
  return cachedAuthRequest<LeadList[]>('/api/v1/lead-lists', idToken, 8000, force)
}

export async function getLeads(idToken: string, listId?: string, force = false): Promise<Lead[]> {
  const query = listId ? `?list_id=${encodeURIComponent(listId)}` : ''
  return cachedAuthRequest<Lead[]>(`/api/v1/leads${query}`, idToken, 7000, force)
}

export async function getLeadDatabaseSnapshot(idToken: string, listId?: string, force = false): Promise<{ lead_lists: LeadList[]; leads: Lead[] }> {
  const query = listId ? `?list_id=${encodeURIComponent(listId)}` : ''
  return cachedAuthRequest<{ lead_lists: LeadList[]; leads: Lead[] }>(`/api/v1/leads/snapshot${query}`, idToken, 7000, force)
}

export type LeadFileImportResult = {
  lead_list: LeadList
  extracted_count: number
  added_count: number
  duplicate_count: number
  skipped_count: number
  detected_columns: Record<string, string>
  leads: Lead[]
}

export async function importLeadFile(idToken: string, file: File, listName?: string): Promise<LeadFileImportResult> {
  const form = new FormData()
  form.append('file', file)
  if (listName?.trim()) form.append('list_name', listName.trim())
  const response = await fetch(`${API_URL}/api/v1/leads/import-file`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${idToken}` },
    body: form,
  })
  if (!response.ok) throw await readError(response, `Import failed with status ${response.status}`)
  return response.json() as Promise<LeadFileImportResult>
}

export function getApiUrl() {
  return API_URL
}

export type ProviderConnection = {
  provider: string
  category: 'search' | 'ai' | 'enrichment'
  label: string
  description: string
  status: string
  connected: boolean
  model: string | null
  key_hint: string | null
  last_validated_at: string | null
  last_error: string | null
}

export type AutomatedSearchStart = {
  lead_list: LeadList
  job_id: string
  status: string
}

export type JobStatus = {
  id: string
  job_type: string
  status: 'pending' | 'running' | 'complete' | 'failed'
  result: {
    list_id?: string
    target_count?: number
    found_count?: number
    progress_percent?: number
    current_step?: string
    search_provider?: string
    ai_provider?: string | null
    queries_completed?: number
    queries_total?: number
    search_calls?: number
    websites_checked?: number
    errors?: string[]
    requested_count?: number
    processed_count?: number
    enriched_count?: number
    verified_email_count?: number
    skipped_count?: number
    failed_count?: number
    provider_counts?: Record<string, number>
  }
  last_error: string | null
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
}

export async function getProviders(idToken: string, force = false): Promise<ProviderConnection[]> {
  return cachedAuthRequest<ProviderConnection[]>('/api/v1/providers', idToken, 12000, force)
}

export async function connectProvider(
  idToken: string,
  provider: string,
  input: { api_key: string; model?: string },
): Promise<ProviderConnection> {
  return authRequest<ProviderConnection>(`/api/v1/providers/${encodeURIComponent(provider)}`, idToken, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export async function disconnectProvider(idToken: string, provider: string): Promise<{ provider: string; connected: false }> {
  return authRequest<{ provider: string; connected: false }>(`/api/v1/providers/${encodeURIComponent(provider)}`, idToken, {
    method: 'DELETE',
  })
}

export async function startAutomatedSearch(
  idToken: string,
  input: {
    niche: string
    location?: string
    target_count: number
    search_provider: 'auto' | 'serper' | 'brave'
    ai_provider: 'auto' | 'none' | 'gemini' | 'openai'
    crawl_websites: boolean
  },
): Promise<AutomatedSearchStart> {
  return authRequest<AutomatedSearchStart>('/api/v1/lead-lists/automated-search', idToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function getJob(idToken: string, jobId: string): Promise<JobStatus> {
  return authRequest<JobStatus>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, idToken)
}


export type EnrichmentStart = {
  job_id: string
  status: string
  selected_count: number
}

export async function startLeadEnrichment(
  idToken: string,
  input: { lead_ids: string[]; provider: 'auto' | 'prospeo' | 'apollo'; target_titles: string[] },
): Promise<EnrichmentStart> {
  return authRequest<EnrichmentStart>('/api/v1/leads/enrich', idToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function downloadLeadExport(
  idToken: string,
  input: {
    format: 'xlsx' | 'csv'
    list_id?: string
    lead_ids?: string[]
    search?: string
    email_filter?: 'all' | 'verified' | 'has_email' | 'missing_email'
    min_score?: number
  },
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_URL}/api/v1/leads/export`, {
    method: 'POST',
    headers: {
      Accept: input.format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  })
  if (!response.ok) {
    throw await readError(response, `Export failed with status ${response.status}`)
  }
  const disposition = response.headers.get('content-disposition') || ''
  const match = disposition.match(/filename=\"?([^\";]+)\"?/i)
  return {
    blob: await response.blob(),
    filename: match?.[1] || `leads.${input.format}`,
  }
}

export type EmailTemplate = {
  id: string
  name: string
  category: string
  subject: string
  body: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type SenderConnection = {
  id: string
  provider: string
  email: string
  display_name: string | null
  status: string
  last_error: string | null
  webhook_status: string
  webhook_url: string | null
  created_at: string
  updated_at: string
}

export type Campaign = {
  id: string
  name: string
  status: string
  template_id: string
  sender_id: string
  sender_email: string | null
  daily_limit: number
  send_start_hour: number
  send_end_hour: number
  timezone: string
  min_interval_seconds: number
  recipient_count: number
  sent_count: number
  failed_count: number
  skipped_count: number
  stop_on_reply: boolean
  replied_count: number
  interested_count: number
  unsubscribed_count: number
  out_of_office_count: number
  approved_at: string | null
  created_at: string
  updated_at: string
}

export type CampaignPreviewItem = { lead_id: string; to_email: string; subject: string; body: string }
export type CampaignCreateResult = {
  campaign: Campaign
  preview: CampaignPreviewItem[]
  suppressed_count: number
  missing_email_count: number
}

export async function getOutreachSnapshot(idToken: string, force = false): Promise<{ templates: EmailTemplate[]; senders: SenderConnection[]; campaigns: Campaign[]; replies: OutreachReply[] }> {
  return cachedAuthRequest<{ templates: EmailTemplate[]; senders: SenderConnection[]; campaigns: Campaign[]; replies: OutreachReply[] }>('/api/v1/outreach/snapshot', idToken, 6000, force)
}

export async function getTemplates(idToken: string, force = false): Promise<EmailTemplate[]> {
  return cachedAuthRequest<EmailTemplate[]>('/api/v1/outreach/templates', idToken, 10000, force)
}
export async function saveTemplate(idToken: string, input: { name: string; category: string; subject: string; body: string }, templateId?: string): Promise<EmailTemplate> {
  const value = await authRequest<EmailTemplate>(templateId ? `/api/v1/outreach/templates/${encodeURIComponent(templateId)}` : '/api/v1/outreach/templates', idToken, {
    method: templateId ? 'PUT' : 'POST', body: JSON.stringify(input),
  })
  invalidateApiCache('/api/v1/outreach/templates')
  return value
}
export async function deleteTemplate(idToken: string, templateId: string): Promise<void> {
  await authRequest(`/api/v1/outreach/templates/${encodeURIComponent(templateId)}`, idToken, { method: 'DELETE' })
  invalidateApiCache('/api/v1/outreach/templates')
}
export async function getSenders(idToken: string, force = false): Promise<SenderConnection[]> {
  return cachedAuthRequest<SenderConnection[]>('/api/v1/outreach/senders', idToken, 10000, force)
}
export async function getGmailAuthorizeUrl(idToken: string): Promise<string> {
  const result = await authRequest<{ authorization_url: string }>('/api/v1/outreach/gmail/authorize-url', idToken)
  return result.authorization_url
}
export async function connectHostingerSender(
  idToken: string,
  input: { api_token: string; mailbox_email?: string; display_name?: string },
): Promise<SenderConnection> {
  const value = await authRequest<SenderConnection>('/api/v1/outreach/hostinger/connect', idToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
  invalidateApiCache('/api/v1/outreach/senders')
  return value
}
export async function disconnectSender(idToken: string, senderId: string): Promise<void> {
  await authRequest(`/api/v1/outreach/senders/${encodeURIComponent(senderId)}`, idToken, { method: 'DELETE' })
  invalidateApiCache('/api/v1/outreach/senders')
}
export async function getCampaigns(idToken: string, force = false): Promise<Campaign[]> {
  return cachedAuthRequest<Campaign[]>('/api/v1/outreach/campaigns', idToken, 6000, force)
}
export async function createCampaign(idToken: string, input: {
  name: string; lead_ids: string[]; template_id: string; sender_id: string; daily_limit: number;
  send_start_hour: number; send_end_hour: number; timezone: string; min_interval_seconds: number; stop_on_reply?: boolean;
  follow_ups?: { template_id: string; delay_hours: number }[];
}): Promise<CampaignCreateResult> {
  const value = await authRequest<CampaignCreateResult>('/api/v1/outreach/campaigns', idToken, { method: 'POST', body: JSON.stringify(input) })
  invalidateApiCache('/api/v1/outreach/campaigns')
  return value
}
export async function campaignAction(idToken: string, campaignId: string, action: 'approve'|'pause'|'resume'|'cancel'): Promise<Campaign> {
  const value = await authRequest<Campaign>(`/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/${action}`, idToken, { method: 'POST' })
  invalidateApiCache('/api/v1/outreach')
  return value
}
export async function suppressEmail(idToken: string, email: string, reason = 'manual'): Promise<void> {
  await authRequest('/api/v1/outreach/suppression', idToken, { method: 'POST', body: JSON.stringify({ email, reason }) })
}

export type QuickSendResult = { sent: boolean; provider_message_id: string; sender_email: string; to_email: string }

export async function quickSend(idToken: string, input: { sender_id: string; to_email: string; subject: string; body: string }): Promise<QuickSendResult> {
  return authRequest<QuickSendResult>('/api/v1/outreach/quick-send', idToken, { method: 'POST', body: JSON.stringify(input) })
}

export async function deleteCampaign(idToken: string, campaignId: string): Promise<void> {
  await authRequest(`/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}`, idToken, { method: 'DELETE' })
  invalidateApiCache('/api/v1/outreach')
}


export type CampaignStep = { id: string; step_number: number; template_id: string; template_name: string | null; delay_hours: number }
export type CampaignMessage = {
  id: string; lead_id: string; company_name: string | null; contact_name: string | null; to_email: string;
  step_number: number; message_kind: string; subject: string; status: string; scheduled_at: string | null;
  sent_at: string | null; replied_at: string | null; last_error: string | null;
}
export type OutreachReply = {
  id: string; campaign_id: string | null; campaign_name: string | null; lead_id: string | null; company_name: string | null;
  from_email: string; to_email: string | null; subject: string | null; snippet: string | null; body_text: string | null;
  classification: 'reply' | 'interested' | 'not_interested' | 'unsubscribe' | 'out_of_office' | string; received_at: string;
}
export type CampaignDetail = {
  campaign: Campaign; steps: CampaignStep[]; messages: CampaignMessage[]; replies: OutreachReply[]; followups_sent: number; reply_rate: number;
}

export async function getCampaignDetail(idToken: string, campaignId: string, force = false): Promise<CampaignDetail> {
  return cachedAuthRequest<CampaignDetail>(`/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}`, idToken, 5000, force)
}
export async function getReplies(idToken: string, force = false): Promise<OutreachReply[]> {
  return cachedAuthRequest<OutreachReply[]>('/api/v1/outreach/replies', idToken, 5000, force)
}
export async function syncSenderReplies(idToken: string, senderId: string): Promise<{ checked_count: number; matched_count: number; new_replies: number }> {
  const result = await authRequest<{ checked_count: number; matched_count: number; new_replies: number }>(`/api/v1/outreach/senders/${encodeURIComponent(senderId)}/sync-replies`, idToken, { method: 'POST' })
  invalidateApiCache('/api/v1/outreach')
  return result
}
export async function retryCampaignMessage(idToken: string, campaignId: string, messageId: string): Promise<void> {
  await authRequest(`/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/messages/${encodeURIComponent(messageId)}/retry`, idToken, { method: 'POST' })
  invalidateApiCache('/api/v1/outreach')
}
export async function deleteLeads(idToken: string, leadIds: string[]): Promise<number> {
  const result = await authRequest<{ deleted_count: number }>('/api/v1/leads/delete', idToken, { method: 'POST', body: JSON.stringify({ lead_ids: leadIds }) })
  invalidateApiCache('/api/v1/leads')
  invalidateApiCache('/api/v1/lead-lists')
  return result.deleted_count
}


export async function setupHostingerWebhook(idToken: string, senderId: string): Promise<{ configured: boolean; url: string }> {
  const value = await authRequest<{ configured: boolean; url: string }>(`/api/v1/outreach/senders/${encodeURIComponent(senderId)}/webhook`, idToken, { method: 'POST' })
  invalidateApiCache('/api/v1/outreach/senders')
  return value
}

export type AdminOverview = {
  users_total: number; users_active: number; users_suspended: number; leads_total: number; lead_lists_total: number;
  campaigns_total: number; emails_sent: number; replies_total: number; jobs_running: number; jobs_failed: number;
  connected_providers: number; connected_senders: number; search_calls: number; websites_checked: number; enriched_contacts: number;
}
export type AdminUser = { firebase_uid: string; email: string | null; display_name: string | null; role: string; status: string; lead_count: number; campaign_count: number; created_at: string; last_login_at: string }
export type AdminJob = { id: string; user_id: string; user_email: string | null; job_type: string; status: string; attempt_count: number; max_attempts: number; last_error: string | null; created_at: string; updated_at: string; started_at: string | null; completed_at: string | null }
export type AdminSystem = { database_ok: boolean; environment: string; api_version: string; public_api_configured: boolean; firebase_configured: boolean; credential_encryption_configured: boolean; background_jobs_mode: string; workers: { worker_name: string; instance_id: string | null; last_seen_at: string; healthy: boolean }[]; providers: { provider: string; connected_count: number; error_count: number }[]; hostinger_webhooks_configured: number }

export async function getAdminOverview(idToken: string, force = false): Promise<AdminOverview> {
  return cachedAuthRequest<AdminOverview>('/api/v1/admin/overview', idToken, 10000, force)
}
export async function getAdminUsers(idToken: string, input: { search?: string; status?: string } = {}, force = false): Promise<{ items: AdminUser[]; total: number }> {
  const params = new URLSearchParams()
  if (input.search) params.set('search', input.search)
  if (input.status) params.set('status', input.status)
  const suffix = params.toString() ? `?${params}` : ''
  return cachedAuthRequest<{ items: AdminUser[]; total: number }>(`/api/v1/admin/users${suffix}`, idToken, 8000, force)
}
export async function updateAdminUserStatus(idToken: string, uid: string, status: 'active'|'suspended'): Promise<AdminUser> {
  const value = await authRequest<AdminUser>(`/api/v1/admin/users/${encodeURIComponent(uid)}/status`, idToken, { method: 'PATCH', body: JSON.stringify({ status }) })
  invalidateApiCache('/api/v1/admin')
  return value
}
export async function getAdminJobs(idToken: string, status = '', force = false): Promise<{ items: AdminJob[]; total: number }> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : ''
  return cachedAuthRequest<{ items: AdminJob[]; total: number }>(`/api/v1/admin/jobs${suffix}`, idToken, 6000, force)
}
export async function retryAdminJob(idToken: string, jobId: string): Promise<AdminJob> {
  const value = await authRequest<AdminJob>(`/api/v1/admin/jobs/${encodeURIComponent(jobId)}/retry`, idToken, { method: 'POST' })
  invalidateApiCache('/api/v1/admin/jobs')
  return value
}
export async function getAdminSystem(idToken: string, force = false): Promise<AdminSystem> {
  return cachedAuthRequest<AdminSystem>('/api/v1/admin/system', idToken, 8000, force)
}
