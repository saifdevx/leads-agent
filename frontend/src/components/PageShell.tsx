import type { ReactNode } from 'react'
import { BrandMark } from './Brand'
import { Icon } from './Icon'
import { StatusBadge } from './StatusBadge'

type Props = {
  title: string
  eyebrow?: string
  healthStatus: 'loading' | 'online' | 'offline'
  onOpenMenu: () => void
  userName?: string | null
  userEmail?: string | null
  onSignOut: () => Promise<void>
  children: ReactNode
}

export function PageShell({ title, eyebrow, healthStatus, onOpenMenu, userName, userEmail, onSignOut, children }: Props) {
  const label = userName || userEmail || 'Account'
  const initial = label.trim().charAt(0).toUpperCase() || 'U'

  return (
    <main className="min-h-screen lg:pl-[248px]">
      <header className="sticky top-0 z-20 border-b border-[#E7E7ED]/90 bg-[#F8F8FB]/88 backdrop-blur-xl supports-[backdrop-filter]:bg-[#F8F8FB]/78">
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-[#7B61FF]/18 to-transparent" />
        <div className="mx-auto flex h-[70px] max-w-[1480px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button onClick={onOpenMenu} className="focus-ring grid h-10 w-10 place-items-center rounded-[10px] border border-[#E2E2E9] bg-white text-[#4B4F5E] shadow-sm lg:hidden" aria-label="Open navigation">
              <Icon name="menu" className="h-5 w-5" />
            </button>
            <div className="lg:hidden"><BrandMark className="h-9 w-9" alt="" /></div>
            <div className="min-w-0">
              {eyebrow && <div className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-[#7B61FF]">{eyebrow}</div>}
              <h1 className="truncate font-display text-[20px] font-extrabold tracking-[-0.025em] text-[#14151C] sm:text-[22px]">{title}</h1>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <StatusBadge status={healthStatus} />
            <div className="hidden h-7 w-px bg-[#E0E0E7] sm:block" />
            <div className="flex min-w-0 items-center gap-2.5">
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-[10px] bg-gradient-to-br from-[#EDE9FF] to-[#F6F4FF] text-xs font-extrabold text-[#654BD9] ring-1 ring-[#DED7FF]">{initial}</div>
              <div className="hidden min-w-0 md:block">
                <div className="max-w-[180px] truncate text-xs font-bold text-[#30323A]">{label}</div>
                {userName && userEmail && <div className="max-w-[180px] truncate text-[10px] text-[#858894]">{userEmail}</div>}
              </div>
            </div>
            <button
              type="button"
              onClick={() => void onSignOut()}
              className="focus-ring grid h-9 w-9 place-items-center rounded-[10px] border border-[#E2E2E8] bg-white text-[#686B77] shadow-sm transition-all hover:-translate-y-px hover:bg-[#FAFAFC] hover:text-[#3B3D45]"
              aria-label="Sign out"
              title="Sign out"
            >
              <Icon name="logout" className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="page-enter mx-auto max-w-[1480px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
    </main>
  )
}
