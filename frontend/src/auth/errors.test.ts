import { describe, expect, it } from 'vitest'
import { getAuthErrorMessage } from './errors'

describe('getAuthErrorMessage', () => {
  it('turns common Firebase errors into readable messages', () => {
    expect(getAuthErrorMessage({ code: 'auth/email-already-in-use' })).toBe(
      'An account already exists with this email.',
    )
  })

  it('uses a safe generic message for unknown errors', () => {
    expect(getAuthErrorMessage(new Error('private provider error'))).toBe(
      'Authentication failed. Please try again.',
    )
  })
})
