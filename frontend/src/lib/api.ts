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

export async function getLeadLists(idToken: string): Promise<LeadList[]> {
  return authRequest<LeadList[]>('/api/v1/lead-lists', idToken)
}

export async function getLeads(idToken: string, listId?: string): Promise<Lead[]> {
  const query = listId ? `?list_id=${encodeURIComponent(listId)}` : ''
  return authRequest<Lead[]>(`/api/v1/leads${query}`, idToken)
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

export async function getProviders(idToken: string): Promise<ProviderConnection[]> {
  return authRequest<ProviderConnection[]>('/api/v1/providers', idToken)
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

export async function getTemplates(idToken: string): Promise<EmailTemplate[]> {
  return authRequest<EmailTemplate[]>('/api/v1/outreach/templates', idToken)
}
export async function saveTemplate(idToken: string, input: { name: string; category: string; subject: string; body: string }, templateId?: string): Promise<EmailTemplate> {
  return authRequest<EmailTemplate>(templateId ? `/api/v1/outreach/templates/${encodeURIComponent(templateId)}` : '/api/v1/outreach/templates', idToken, {
    method: templateId ? 'PUT' : 'POST', body: JSON.stringify(input),
  })
}
export async function deleteTemplate(idToken: string, templateId: string): Promise<void> {
  await authRequest(`/api/v1/outreach/templates/${encodeURIComponent(templateId)}`, idToken, { method: 'DELETE' })
}
export async function getSenders(idToken: string): Promise<SenderConnection[]> {
  return authRequest<SenderConnection[]>('/api/v1/outreach/senders', idToken)
}
export async function getGmailAuthorizeUrl(idToken: string): Promise<string> {
  const result = await authRequest<{ authorization_url: string }>('/api/v1/outreach/gmail/authorize-url', idToken)
  return result.authorization_url
}
export async function connectHostingerSender(
  idToken: string,
  input: { api_token: string; mailbox_email?: string; display_name?: string },
): Promise<SenderConnection> {
  return authRequest<SenderConnection>('/api/v1/outreach/hostinger/connect', idToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
export async function disconnectSender(idToken: string, senderId: string): Promise<void> {
  await authRequest(`/api/v1/outreach/senders/${encodeURIComponent(senderId)}`, idToken, { method: 'DELETE' })
}
export async function getCampaigns(idToken: string): Promise<Campaign[]> {
  return authRequest<Campaign[]>('/api/v1/outreach/campaigns', idToken)
}
export async function createCampaign(idToken: string, input: {
  name: string; lead_ids: string[]; template_id: string; sender_id: string; daily_limit: number;
  send_start_hour: number; send_end_hour: number; timezone: string; min_interval_seconds: number;
}): Promise<CampaignCreateResult> {
  return authRequest<CampaignCreateResult>('/api/v1/outreach/campaigns', idToken, { method: 'POST', body: JSON.stringify(input) })
}
export async function campaignAction(idToken: string, campaignId: string, action: 'approve'|'pause'|'resume'|'cancel'): Promise<Campaign> {
  return authRequest<Campaign>(`/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/${action}`, idToken, { method: 'POST' })
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
}
