import { afterEach, describe, expect, it, vi } from 'vitest'
import { createSearchPlan, getAuthenticatedUser, getHealth, getLeads, importLeadText, ApiRequestError } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getHealth', () => {
  it('returns the structured health payload', async () => {
    const payload = {
      status: 'ok' as const,
      service: 'lead-gen-api',
      version: '0.5.0',
      environment: 'test',
      timestamp: '2026-09-17T00:00:00Z',
      request_id: 'test-request',
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }))
    await expect(getHealth()).resolves.toEqual(payload)
  })

  it('throws when the API is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ error: { message: 'Service unavailable' } }),
    }))
    await expect(getHealth()).rejects.toMatchObject({ name: 'ApiRequestError', status: 503, message: 'Service unavailable' })
  })
})

describe('authenticated API requests', () => {
  it('sends the Firebase token when verifying the user', async () => {
    const payload = { uid: 'firebase-123', email: 'user@example.com', name: 'Example User', email_verified: true, sign_in_provider: 'password' }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetchMock)
    await expect(getAuthenticatedUser('firebase-token')).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/auth/me'), expect.objectContaining({ headers: expect.any(Headers) }))
    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer firebase-token')
  })

  it('creates a free search plan', async () => {
    const payload = { lead_list: { id: 'list-1' }, queries: ['query'] }
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetchMock)
    await createSearchPlan('token', { niche: 'Solar', location: 'Texas', target_count: 100 })
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/lead-lists/plan'), expect.objectContaining({ method: 'POST' }))
  })

  it('imports pasted lead text', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ extracted_count: 1, added_count: 1, duplicate_count: 0, skipped_count: 0, leads: [] }) })
    vi.stubGlobal('fetch', fetchMock)
    await importLeadText('token', 'list-1', { raw_text: 'hello@example.com' })
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/lead-lists/list-1/import-text'), expect.objectContaining({ method: 'POST' }))
  })

  it('loads leads for a selected list', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)
    await getLeads('token', 'list-1')
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/leads?list_id=list-1'), expect.anything())
  })

  it('surfaces backend authentication messages', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ error: { message: 'Session expired', request_id: 'req-1' } }) }))
    try {
      await getAuthenticatedUser('expired')
      throw new Error('Expected request to fail')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiRequestError)
      expect(error).toMatchObject({ status: 401, message: 'Session expired', requestId: 'req-1' })
    }
  })
})
