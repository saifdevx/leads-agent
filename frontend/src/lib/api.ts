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
  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    signal,
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${idToken}`,
    },
  })

  if (!response.ok) {
    throw await readError(response, `Authentication verification failed with status ${response.status}`)
  }

  return response.json() as Promise<AuthenticatedUserResponse>
}

export function getApiUrl() {
  return API_URL
}
