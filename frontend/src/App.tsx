import { useEffect, useState } from 'react'
import { PageShell } from './components/PageShell'
import { Sidebar } from './components/Sidebar'
import { FindLeadsPage } from './pages/FindLeadsPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { getHealth } from './lib/api'

type PageKey = 'find' | 'leads' | 'outreach' | 'settings'

type HealthState = 'loading' | 'online' | 'offline'

const pageMeta: Record<PageKey, { title: string; eyebrow?: string }> = {
  find: { title: 'Find Leads', eyebrow: 'Lead discovery' },
  leads: { title: 'My Leads', eyebrow: 'Lead database' },
  outreach: { title: 'Outreach', eyebrow: 'Email campaigns' },
  settings: { title: 'Settings', eyebrow: 'Configuration' },
}

export default function App() {
  const [page, setPage] = useState<PageKey>('find')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [health, setHealth] = useState<HealthState>('loading')
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 4000)

    getHealth(controller.signal)
      .then(() => setHealth('online'))
      .catch(() => setHealth('offline'))
      .finally(() => window.clearTimeout(timer))

    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 4500)
    return () => window.clearTimeout(timer)
  }, [notice])

  let content
  if (page === 'find') {
    content = <FindLeadsPage onFoundationAction={setNotice} />
  } else if (page === 'leads') {
    content = <PlaceholderPage title="My Leads" description="One clean table will hold the leads you discover. We will keep company and contact details together in the first version instead of exposing CRM-style complexity." icon="users" checkpoint="Lead Management" bullets={['Search and filter', 'Email and phone status', 'Lead score', 'Excel export']} />
  } else if (page === 'outreach') {
    content = <PlaceholderPage title="Outreach" description="Outreach will stay intentionally simple: choose leads, select a template and sender, preview the batch, then approve the campaign." icon="mail" checkpoint="Outreach" bullets={['User templates', 'Gmail sender', 'Daily limits', 'Pause and resume']} />
  } else {
    content = <PlaceholderPage title="Settings" description="All user configuration will live in one place. Providers, AI and email connections will be grouped into clear tabs rather than scattered across technical pages." icon="settings" checkpoint="Integrations" bullets={['Search providers', 'Gemini / OpenAI', 'Enrichment providers', 'Email connections']} />
  }

  return (
    <div>
      <Sidebar active={page} onNavigate={setPage} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <PageShell title={pageMeta[page].title} eyebrow={pageMeta[page].eyebrow} healthStatus={health} onOpenMenu={() => setMobileOpen(true)}>
        {content}
      </PageShell>

      {notice && (
        <div role="status" className="fixed bottom-5 right-5 z-[80] max-w-[420px] rounded-[12px] border border-[#DCD9EB] bg-white px-4 py-3.5 text-sm font-medium leading-5 text-[#333640] shadow-[0_16px_45px_rgba(20,21,28,0.15)]">
          <div className="mb-1 text-xs font-bold uppercase tracking-[0.09em] text-[#7B61FF]">Checkpoint 1</div>
          {notice}
        </div>
      )}
    </div>
  )
}
