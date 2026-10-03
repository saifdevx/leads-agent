import type { ProviderConnection } from './api'

export type SearchProvider = 'auto' | 'serper' | 'brave' | 'apollo'

// Apollo intentionally stays in the enrichment category in Settings. It also
// supports company discovery; a single-category filter cannot express both.
export const SEARCH_SOURCES = [
  { id: 'serper', label: 'Serper / Google' },
  { id: 'brave', label: 'Brave Search' },
  { id: 'apollo', label: 'Apollo / Companies' },
] as const

export function connectedSearchProviders(providers: ProviderConnection[]) {
  return providers.filter((provider) => provider.connected &&
    SEARCH_SOURCES.some((source) => source.id === provider.provider))
}

export function searchReady(providers: ProviderConnection[], selected: SearchProvider) {
  const connected = connectedSearchProviders(providers)
  return selected === 'auto' ? connected.length > 0 : connected.some((item) => item.provider === selected)
}

export function usesApolloSearch(providers: ProviderConnection[], selected: SearchProvider) {
  const connected = connectedSearchProviders(providers)
  return selected === 'apollo' || (selected === 'auto' && connected.length === 1 && connected[0].provider === 'apollo')
}
