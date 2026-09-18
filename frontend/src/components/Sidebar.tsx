import { Icon, type IconName } from './Icon'

type NavKey = 'find' | 'leads' | 'outreach' | 'settings'

type Props = {
  active: NavKey
  onNavigate: (key: NavKey) => void
  mobileOpen: boolean
  onMobileClose: () => void
}

const items: Array<{ key: NavKey; label: string; icon: IconName }> = [
  { key: 'find', label: 'Find Leads', icon: 'search' },
  { key: 'leads', label: 'My Leads', icon: 'users' },
  { key: 'outreach', label: 'Outreach', icon: 'mail' },
  { key: 'settings', label: 'Settings', icon: 'settings' },
]

export function Sidebar({ active, onNavigate, mobileOpen, onMobileClose }: Props) {
  const content = (
    <div className="flex h-full flex-col bg-[#14151C] px-4 py-5 text-white">
      <div className="flex items-center justify-between px-2">
        <button className="focus-ring flex items-center gap-3 rounded-lg text-left" onClick={() => onNavigate('find')}>
          <div className="grid h-9 w-9 place-items-center rounded-[10px] bg-[#7B61FF] font-display text-sm font-extrabold tracking-tight">LP</div>
          <div>
            <div className="font-display text-[15px] font-bold tracking-[-0.01em]">Lead Platform</div>
            <div className="mt-0.5 text-[11px] text-white/45">Free-first prospecting</div>
          </div>
        </button>
        <button onClick={onMobileClose} className="focus-ring rounded-lg p-2 text-white/70 hover:bg-white/10 lg:hidden" aria-label="Close navigation">
          <Icon name="close" className="h-5 w-5" />
        </button>
      </div>

      <nav className="mt-9 space-y-1" aria-label="Primary navigation">
        {items.map((item) => {
          const selected = item.key === active
          return (
            <button
              key={item.key}
              onClick={() => {
                onNavigate(item.key)
                onMobileClose()
              }}
              className={`focus-ring flex w-full items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm font-semibold transition ${selected ? 'bg-white text-[#14151C]' : 'text-white/68 hover:bg-white/8 hover:text-white'}`}
            >
              <Icon name={item.icon} className={`h-[18px] w-[18px] ${selected ? 'text-[#7B61FF]' : ''}`} />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="mt-auto rounded-[10px] border border-white/8 bg-white/[0.035] p-3.5">
        <div className="text-xs font-semibold text-white/75">Simple by design</div>
        <p className="mt-1.5 text-[11px] leading-5 text-white/42">Find leads, review them, then reach out. Advanced systems stay in the background.</p>
      </div>
    </div>
  )

  return (
    <>
      <aside className="fixed inset-y-0 left-0 hidden w-[238px] lg:block">{content}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button className="absolute inset-0 bg-black/35" aria-label="Close navigation overlay" onClick={onMobileClose} />
          <aside className="relative h-full w-[280px] max-w-[88vw] shadow-2xl">{content}</aside>
        </div>
      )}
    </>
  )
}
