import type { ProviderConnection } from './api'

export type SearchProvider = string
export type Capability = 'search' | 'ai' | 'enrichment'

// The backend catalogue is authoritative. Adding an implemented adapter there
// automatically exposes it here; an API key alone does not create an adapter.
export function supports(provider: ProviderConnection, capability: Capability) {
  return provider.capabilities?.includes(capability) ?? provider.category === capability
}

export function providersFor(providers: ProviderConnection[], capability: Capability) {
  return providers.filter((provider) => supports(provider, capability))
    .sort((a, b) => (a.priority ?? 100) - (b.priority ?? 100) || a.label.localeCompare(b.label))
}

export function searchSources(providers: ProviderConnection[]) {
  return providersFor(providers, 'search').map((provider) => ({
    id: provider.provider,
    label: provider.discovery_kind === 'companies' ? `${provider.label} / Companies` : provider.label,
    connected: provider.connected,
  }))
}

export function connectedSearchProviders(providers: ProviderConnection[]) {
  return providersFor(providers, 'search').filter((provider) => provider.connected)
}

export function searchReady(providers: ProviderConnection[], selected: SearchProvider) {
  const connected = connectedSearchProviders(providers)
  return selected === 'auto' ? connected.length > 0 : connected.some((item) => item.provider === selected)
}

export function selectedSearchProviders(providers: ProviderConnection[], selected: SearchProvider) {
  const connected = connectedSearchProviders(providers)
  if (selected !== 'auto') return connected.filter((provider) => provider.provider === selected)
  const web = connected.filter((provider) => provider.discovery_kind !== 'companies')
  return web.length ? web : connected
}
