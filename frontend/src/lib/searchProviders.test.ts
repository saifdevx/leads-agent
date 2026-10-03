import { describe, expect, it } from 'vitest'
import { connectedSearchProviders, searchReady, searchSources, selectedSearchProviders, providersFor } from './searchProviders'
import type { ProviderConnection } from './api'

function provider(name: string, capabilities: string[], connected = true, kind: 'web' | 'companies' = 'web', priority = 10): ProviderConnection {
  return { provider: name, label: name, connected, capabilities, discovery_kind: kind, priority,
    category: capabilities.includes('enrichment') ? 'enrichment' : capabilities.includes('ai') ? 'ai' : 'search',
    description: '', status: connected ? 'connected' : 'disconnected',
    model: null, key_hint: null, last_validated_at: null, last_error: null }
}

describe('server-driven connector capabilities', () => {
  it('surfaces both company-search databases despite their legacy enrichment category', () => {
    for (const name of ['apollo', 'prospeo']) {
      const items = [provider(name, ['search', 'enrichment'], true, 'companies')]
      expect(searchReady(items, 'auto')).toBe(true)
      expect(searchReady(items, name)).toBe(true)
      expect(searchSources(items)[0].label).toBe(`${name} / Companies`)
      expect(providersFor(items, 'enrichment')).toHaveLength(1)
    }
  })
  it('surfaces new search providers without a client-side name list', () => {
    const items = [provider('future-adapter', ['search'])]
    expect(connectedSearchProviders(items)[0].provider).toBe('future-adapter')
    expect(searchReady(items, 'future-adapter')).toBe(true)
  })
  it('never enables a disconnected selection', () => {
    expect(searchReady([provider('exa', ['search'], false)], 'exa')).toBe(false)
    expect(searchReady([provider('tavily', ['search'])], 'exa')).toBe(false)
  })
  it('does not turn AI or enrichment-only adapters into search engines', () => {
    const items = [provider('openai', ['ai']), provider('contacts-only', ['enrichment'])]
    expect(searchReady(items, 'auto')).toBe(false)
    expect(searchSources(items)).toEqual([])
  })
  it('matches the backend web-first policy and explicit selection', () => {
    const items = [provider('apollo', ['search', 'enrichment'], true, 'companies', 60), provider('tavily', ['search'], true, 'web', 30)]
    expect(selectedSearchProviders(items, 'auto').map((x) => x.provider)).toEqual(['tavily'])
    expect(selectedSearchProviders(items, 'apollo').map((x) => x.provider)).toEqual(['apollo'])
  })
  it('orders company-only failover by server priority', () => {
    const items = [provider('apollo', ['search'], true, 'companies', 60), provider('prospeo', ['search'], true, 'companies', 50)]
    expect(selectedSearchProviders(items, 'auto').map((x) => x.provider)).toEqual(['prospeo', 'apollo'])
  })
  it('supports the old backend category for single-capability providers', () => {
    const old = provider('brave', ['search']); delete old.capabilities
    expect(searchReady([old], 'auto')).toBe(true)
  })
})
