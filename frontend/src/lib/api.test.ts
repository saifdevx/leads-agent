import { afterEach, describe, expect, it, vi } from 'vitest'
import { getHealth } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getHealth', () => {
  it('returns the structured health payload', async () => {
    const payload = {
      status: 'ok' as const,
      service: 'lead-platform-api',
      version: '0.1.0',
      environment: 'test',
      timestamp: '2026-09-15T00:00:00Z',
      request_id: 'test-request',
    }

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    }))

    await expect(getHealth()).resolves.toEqual(payload)
  })

  it('throws when the API is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    await expect(getHealth()).rejects.toThrow('Health check failed with status 503')
  })
})
