import type { ReactNode } from 'react'
import { Icon } from './Icon'
import { StatusBadge } from './StatusBadge'

type Props = {
  title: string
  eyebrow?: string
  healthStatus: 'loading' | 'online' | 'offline'
  onOpenMenu: () => void
  children: ReactNode
}

export function PageShell({ title, eyebrow, healthStatus, onOpenMenu, children }: Props) {
  return (
    <main className="min-h-screen lg:pl-[238px]">
      <header className="sticky top-0 z-20 border-b border-[#E7E7ED] bg-[#F7F7FA]/92 backdrop-blur-xl">
        <div className="mx-auto flex h-[68px] max-w-[1460px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button onClick={onOpenMenu} className="focus-ring rounded-lg border border-[#E3E3E9] bg-white p-2 text-[#4B4F5E] lg:hidden" aria-label="Open navigation">
              <Icon name="menu" className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              {eyebrow && <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#7B61FF]">{eyebrow}</div>}
              <h1 className="truncate font-display text-[19px] font-bold tracking-[-0.02em] text-[#14151C] sm:text-[21px]">{title}</h1>
            </div>
          </div>
          <StatusBadge status={healthStatus} />
        </div>
      </header>

      <div className="mx-auto max-w-[1460px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</div>
    </main>
  )
}
