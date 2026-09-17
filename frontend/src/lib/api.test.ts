import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError, getAuthenticatedUser, getHealth } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getHealth', () => {
  it('returns the structured health payload', async () => {
    const payload = {
      status: 'ok' as const,
      service: 'lead-platform-api',
      version: '0.3.0',
      environment: 'test',
      timestamp: '2026-09-16T00:00:00Z',
      request_id: 'test-request',
    }

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    }))

    await expect(getHealth()).resolves.toEqual(payload)
  })

  it('throws when the API is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ error: { message: 'Service unavailable' } }),
    }))

    await expect(getHealth()).rejects.toMatchObject({
      name: 'ApiRequestError',
      status: 503,
      message: 'Service unavailable',
    })
  })
})

describe('getAuthenticatedUser', () => {
  it('sends the Firebase token to the backend', async () => {
    const payload = {
      uid: 'firebase-123',
      email: 'user@example.com',
      name: 'Example User',
      email_verified: true,
      sign_in_provider: 'password',
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(getAuthenticatedUser('firebase-token')).resolves.toEqual(payload)
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/me'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer firebase-token' }),
      }),
    )
  })

  it('surfaces the backend authentication message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ error: { message: 'Session expired', request_id: 'req-1' } }),
    }))

    try {
      await getAuthenticatedUser('expired')
      throw new Error('Expected request to fail')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiRequestError)
      expect(error).toMatchObject({ status: 401, message: 'Session expired', requestId: 'req-1' })
    }
  })
})
