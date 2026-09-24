import { BrandLockup } from './Brand'
import { Icon, type IconName } from './Icon'

type NavKey = 'find' | 'leads' | 'outreach' | 'settings' | 'admin'

type Props = {
  active: NavKey
  onNavigate: (key: NavKey) => void
  mobileOpen: boolean
  onMobileClose: () => void
  isAdmin?: boolean
}

const items: Array<{ key: NavKey; label: string; icon: IconName }> = [
  { key: 'find', label: 'Find Leads', icon: 'search' },
  { key: 'leads', label: 'My Leads', icon: 'users' },
  { key: 'outreach', label: 'Outreach', icon: 'mail' },
  { key: 'settings', label: 'Settings', icon: 'settings' },
]

export function Sidebar({ active, onNavigate, mobileOpen, onMobileClose, isAdmin = false }: Props) {
  const content = (
    <div className="relative flex h-full flex-col overflow-hidden bg-[#14151C] px-4 py-5 text-white">
      <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-[#7B61FF]/12 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-20 h-56 w-56 rounded-full bg-[#BCE953]/8 blur-3xl" />

      <div className="relative flex items-center justify-between px-2">
        <button className="focus-ring rounded-xl text-left" onClick={() => onNavigate('find')} aria-label="Go to Find Leads">
          <BrandLockup compact light subtitle="Prospecting workspace" />
        </button>
        <button onClick={onMobileClose} className="focus-ring rounded-lg p-2 text-white/70 hover:bg-white/10 lg:hidden" aria-label="Close navigation">
          <Icon name="close" className="h-5 w-5" />
        </button>
      </div>

      <nav className="relative mt-9 space-y-1" aria-label="Primary navigation">
        {[...items, ...(isAdmin ? [{ key: 'admin' as NavKey, label: 'Admin', icon: 'shield' as IconName }] : [])].map((item) => {
          const selected = item.key === active
          return (
            <button
              key={item.key}
              onClick={() => {
                onNavigate(item.key)
                onMobileClose()
              }}
              className={`focus-ring group flex w-full items-center gap-3 rounded-[11px] px-3 py-2.5 text-sm font-semibold transition-all duration-200 ${selected ? 'bg-white text-[#14151C] shadow-[0_8px_20px_rgba(0,0,0,.12)]' : 'text-white/66 hover:bg-white/8 hover:text-white'}`}
            >
              <span className={`grid h-7 w-7 place-items-center rounded-lg transition ${selected ? 'bg-[#F0EDFF] text-[#7B61FF]' : 'bg-white/[0.04] text-white/64 group-hover:bg-white/[0.08] group-hover:text-white'}`}>
                <Icon name={item.icon} className="h-[16px] w-[16px]" />
              </span>
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="relative mt-auto rounded-[12px] border border-white/8 bg-white/[0.04] p-4 shadow-inner">
        <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.08em] text-white/56">
          <span className="h-2 w-2 rounded-full bg-[#BCE953] shadow-[0_0_0_4px_rgba(188,233,83,.08)]" />
          Focused workflow
        </div>
        <p className="mt-2 text-[11px] leading-5 text-white/43">Find. Enrich. Reach out. The technical work stays behind the interface.</p>
      </div>
    </div>
  )

  return (
    <>
      <aside className="fixed inset-y-0 left-0 hidden w-[248px] lg:block">{content}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" aria-label="Close navigation overlay" onClick={onMobileClose} />
          <aside className="drawer-enter relative h-full w-[286px] max-w-[88vw] shadow-2xl">{content}</aside>
        </div>
      )}
    </>
  )
}
