import { useCallback, useEffect, useState } from 'react'
import type { User } from 'firebase/auth'
import { useAuth } from './auth/AuthContext'
import { PageShell } from './components/PageShell'
import { Sidebar } from './components/Sidebar'
import { ApiRequestError, getAuthenticatedUser, getHealth, type AuthenticatedUserResponse } from './lib/api'
import { AuthLoadingPage } from './pages/AuthLoadingPage'
import { AuthPage } from './pages/AuthPage'
import { AuthSetupPage } from './pages/AuthSetupPage'
import { AuthVerificationErrorPage } from './pages/AuthVerificationErrorPage'
import { FindLeadsPage } from './pages/FindLeadsPage'
import { MyLeadsPage } from './pages/MyLeadsPage'
import { OutreachPage } from './pages/OutreachPage'
import { SettingsPage } from './pages/SettingsPage'
import { AdminPage } from './pages/AdminPage'

type PageKey = 'find' | 'leads' | 'outreach' | 'settings' | 'admin'
type HealthState = 'loading' | 'online' | 'offline'

const pageMeta: Record<PageKey, { title: string; eyebrow?: string }> = {
  find: { title: 'Find Leads', eyebrow: 'Lead discovery' },
  leads: { title: 'My Leads', eyebrow: 'Lead database' },
  outreach: { title: 'Outreach', eyebrow: 'Email campaigns' },
  settings: { title: 'Settings', eyebrow: 'Configuration' },
  admin: { title: 'Admin', eyebrow: 'Platform operations' },
}

function Workspace({ user, identity, onSignOut }: { user: User; identity: AuthenticatedUserResponse; onSignOut: () => Promise<void> }) {
  const [page, setPage] = useState<PageKey>(() => new URLSearchParams(window.location.search).has('gmail') ? 'outreach' : 'find')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [health, setHealth] = useState<HealthState>('loading')
  const [outreachLeadIds, setOutreachLeadIds] = useState<string[]>([])
  const getToken = useCallback(() => user.getIdToken(), [user])

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

  let content
  if (page === 'find') {
    content = <FindLeadsPage getToken={getToken} onViewLeads={() => setPage('leads')} onOpenSettings={() => setPage('settings')} />
  } else if (page === 'leads') {
    content = <MyLeadsPage getToken={getToken} onStartOutreach={(ids) => { setOutreachLeadIds(ids); setPage('outreach') }} />
  } else if (page === 'outreach') {
    content = <OutreachPage getToken={getToken} initialLeadIds={outreachLeadIds} onClearInitialLeadIds={() => setOutreachLeadIds([])} onOpenLeads={() => setPage('leads')} />
  } else if (page === 'settings') {
    content = <SettingsPage getToken={getToken} />
  } else if (identity.role === 'admin') {
    content = <AdminPage getToken={getToken} />
  } else {
    content = <FindLeadsPage getToken={getToken} onViewLeads={() => setPage('leads')} onOpenSettings={() => setPage('settings')} />
  }

  return (
    <div>
      <Sidebar active={page} onNavigate={setPage} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} isAdmin={identity.role === 'admin'} />
      <PageShell
        title={pageMeta[page].title}
        eyebrow={pageMeta[page].eyebrow}
        healthStatus={health}
        onOpenMenu={() => setMobileOpen(true)}
        userName={identity.name || user.displayName}
        userEmail={identity.email || user.email}
        onSignOut={onSignOut}
      >
        {content}
      </PageShell>
    </div>
  )
}

function VerifiedWorkspace({ user, onSignOut }: { user: User; onSignOut: () => Promise<void> }) {
  const [identity, setIdentity] = useState<AuthenticatedUserResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    setIdentity(null)
    setError(null)

    user.getIdToken()
      .then((token) => getAuthenticatedUser(token, controller.signal))
      .then((nextIdentity) => {
        if (active) setIdentity(nextIdentity)
      })
      .catch((nextError) => {
        if (!active) return
        if (nextError instanceof ApiRequestError) {
          setError(nextError.message)
        } else {
          setError('The backend could not verify your Firebase session. Check that the API, Firebase Admin credentials and Turso database are configured.')
        }
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [user, attempt])

  if (error) {
    return <AuthVerificationErrorPage message={error} onRetry={() => setAttempt((value) => value + 1)} onSignOut={() => void onSignOut()} />
  }

  if (!identity) {
    return <AuthLoadingPage label="Verifying your account…" />
  }

  return <Workspace user={user} identity={identity} onSignOut={onSignOut} />
}

export default function App() {
  const { user, loading, configured, signOut } = useAuth()

  if (!configured) return <AuthSetupPage />
  if (loading) return <AuthLoadingPage />
  if (!user) return <AuthPage />

  return <VerifiedWorkspace user={user} onSignOut={signOut} />
}
