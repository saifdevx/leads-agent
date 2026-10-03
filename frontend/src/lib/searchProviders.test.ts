import { describe, expect, it } from 'vitest'
import { connectedSearchProviders, searchReady, usesApolloSearch } from './searchProviders'
import type { ProviderConnection } from './api'

function provider(name: string, connected = true): ProviderConnection {
  return { provider: name, label: name, connected,
    category: name === 'apollo' || name === 'prospeo' ? 'enrichment' : name === 'openai' ? 'ai' : 'search',
    description: '', status: connected ? 'connected' : 'disconnected',
    model: null, key_hint: null, last_validated_at: null, last_error: null }
}

describe('discovery provider capabilities', () => {
  it('recognizes Apollo despite its existing enrichment category', () => {
    expect(connectedSearchProviders([provider('apollo')]).map((item) => item.provider)).toEqual(['apollo'])
    expect(searchReady([provider('apollo')], 'auto')).toBe(true)
    expect(searchReady([provider('apollo')], 'apollo')).toBe(true)
    expect(usesApolloSearch([provider('apollo')], 'auto')).toBe(true)
  })
  it('does not enable a disconnected selected source', () => {
    expect(searchReady([provider('serper'), provider('apollo', false)], 'apollo')).toBe(false)
    expect(searchReady([provider('apollo')], 'brave')).toBe(false)
  })
  it('does not treat AI or enrichment-only providers as search', () => {
    expect(searchReady([provider('openai'), provider('prospeo')], 'auto')).toBe(false)
  })
  it('preserves web-search auto selection when web and Apollo are connected', () => {
    expect(usesApolloSearch([provider('serper'), provider('apollo')], 'auto')).toBe(false)
    expect(usesApolloSearch([provider('serper'), provider('apollo')], 'apollo')).toBe(true)
  })
})
