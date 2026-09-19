import { useEffect, useMemo, useState } from 'react'
import { Icon } from '../components/Icon'
import { ApiRequestError, connectProvider, disconnectProvider, getProviders, type ProviderConnection } from '../lib/api'

type Props = { getToken: () => Promise<string> }

type Draft = { provider: ProviderConnection; apiKey: string; model: string }

const providerOrder = ['serper', 'brave', 'gemini', 'openai']

export function SettingsPage({ getToken }: Props) {
  const [providers, setProviders] = useState<ProviderConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      setProviders(await getProviders(token))
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not load integrations.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const ordered = useMemo(() => [...providers].sort((a, b) => providerOrder.indexOf(a.provider) - providerOrder.indexOf(b.provider)), [providers])

  async function saveDraft() {
    if (!draft || !draft.apiKey.trim()) return
    setSaving(true)
    setError(null)
    try {
      const token = await getToken()
      const next = await connectProvider(token, draft.provider.provider, {
        api_key: draft.apiKey.trim(),
        model: draft.model.trim() || undefined,
      })
      setProviders((current) => current.map((item) => item.provider === next.provider ? next : item))
      setDraft(null)
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not connect this provider.')
    } finally {
      setSaving(false)
    }
  }

  async function disconnect(provider: ProviderConnection) {
    setSaving(true)
    setError(null)
    try {
      const token = await getToken()
      await disconnectProvider(token, provider.provider)
      await load()
    } catch (nextError) {
      setError(nextError instanceof ApiRequestError ? nextError.message : 'Could not disconnect this provider.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className="card-surface rounded-[14px] p-5 sm:p-7">
        <div className="max-w-[700px]">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#F0EDFF] px-3 py-1.5 text-xs font-bold text-[#6D52EE]">
            <Icon name="settings" className="h-3.5 w-3.5" /> Bring your own keys
          </div>
          <h2 className="font-display text-2xl font-bold tracking-[-0.03em] text-[#1C1E25]">Connect the services you want to use.</h2>
          <p className="mt-2 text-sm leading-6 text-[#666A75]">Keys are validated by the backend, encrypted before they are stored, and never returned to the browser after saving.</p>
        </div>
      </section>

      {error && <div className="rounded-[10px] border border-[#F0CBC8] bg-[#FFF6F5] px-4 py-3 text-sm font-medium text-[#9D3D36]">{error}</div>}

      {loading ? (
        <div className="card-surface grid min-h-[220px] place-items-center rounded-[14px] text-sm font-medium text-[#777A87]">Loading integrations…</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {ordered.map((provider) => (
            <article key={provider.provider} className="card-surface rounded-[14px] p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-display text-lg font-bold text-[#24262D]">{provider.label}</h3>
                    <span className={`rounded-md px-2 py-1 text-[10px] font-extrabold uppercase tracking-[0.06em] ${provider.connected ? 'bg-[#F0F8DC] text-[#688328]' : 'bg-[#F2F1F6] text-[#777A87]'}`}>
                      {provider.connected ? 'Connected' : provider.category === 'ai' ? 'Optional AI' : 'Search'}
                    </span>
                  </div>
                  <p className="mt-2 max-w-[520px] text-sm leading-6 text-[#6F727E]">{provider.description}</p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#ECECF1] pt-4">
                <div className="text-xs text-[#777A87]">
                  {provider.connected ? (
                    <span>{provider.key_hint}{provider.model ? ` · ${provider.model}` : ''}</span>
                  ) : (
                    <span>{provider.provider === 'serper' ? 'Best match for Google-style prospecting.' : provider.provider === 'brave' ? 'Useful secondary web coverage.' : 'Improves cleanup and relevance filtering.'}</span>
                  )}
                </div>
                <div className="flex gap-2">
                  {provider.connected && (
                    <button type="button" disabled={saving} onClick={() => void disconnect(provider)} className="focus-ring h-9 rounded-[8px] border border-[#E0E0E7] bg-white px-3 text-xs font-bold text-[#6C6F79] hover:bg-[#F8F8FA] disabled:opacity-60">Disconnect</button>
                  )}
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => setDraft({ provider, apiKey: '', model: provider.model || '' })}
                    className="focus-ring h-9 rounded-[8px] bg-[#7B61FF] px-3.5 text-xs font-bold text-white hover:bg-[#6C52EE] disabled:opacity-60"
                  >
                    {provider.connected ? 'Replace key' : 'Connect'}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {draft && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#14151C]/45 p-4" onMouseDown={(event) => { if (event.currentTarget === event.target && !saving) setDraft(null) }}>
          <div className="w-full max-w-[520px] rounded-[16px] border border-white/20 bg-white p-6 shadow-2xl sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.08em] text-[#7B61FF]">Integration</p>
                <h3 className="mt-1 font-display text-xl font-bold text-[#22242B]">Connect {draft.provider.label}</h3>
              </div>
              <button type="button" disabled={saving} onClick={() => setDraft(null)} className="focus-ring grid h-9 w-9 place-items-center rounded-lg text-[#777A87] hover:bg-[#F3F3F6]"><Icon name="close" className="h-4 w-4" /></button>
            </div>

            <label className="mt-6 block">
              <span className="mb-2 block text-[13px] font-semibold text-[#343741]">API key</span>
              <input type="password" autoComplete="off" value={draft.apiKey} onChange={(event) => setDraft((current) => current ? { ...current, apiKey: event.target.value } : current)} placeholder="Paste your API key" className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] px-4 text-sm" />
            </label>

            {draft.provider.category === 'ai' && (
              <label className="mt-4 block">
                <span className="mb-2 block text-[13px] font-semibold text-[#343741]">Model</span>
                <input value={draft.model} onChange={(event) => setDraft((current) => current ? { ...current, model: event.target.value } : current)} className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] px-4 text-sm" />
                <p className="mt-2 text-xs leading-5 text-[#858894]">You can keep the suggested low-cost model or enter another compatible model ID.</p>
              </label>
            )}

            <div className="mt-6 rounded-[10px] bg-[#F8F7FC] px-4 py-3 text-xs leading-5 text-[#6E717D]">The backend validates this key before saving it. AI connections run one tiny generation test so unusable project/model access is caught immediately. The plaintext key is not returned after storage.</div>

            <div className="mt-6 flex justify-end gap-2">
              <button type="button" disabled={saving} onClick={() => setDraft(null)} className="focus-ring h-10 rounded-[9px] border border-[#DDDDE4] px-4 text-sm font-bold text-[#62656F]">Cancel</button>
              <button type="button" disabled={saving || draft.apiKey.trim().length < 4} onClick={() => void saveDraft()} className="focus-ring h-10 rounded-[9px] bg-[#7B61FF] px-4 text-sm font-bold text-white hover:bg-[#6D53EF] disabled:opacity-50">{saving ? 'Validating…' : 'Connect'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
