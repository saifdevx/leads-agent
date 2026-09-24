type MarkProps = {
  className?: string
  alt?: string
}

export function BrandMark({ className = 'h-10 w-10', alt = 'Lead Gen' }: MarkProps) {
  return (
    <img
      src="/leadgen-mark.png"
      alt={alt}
      className={`${className} rounded-[11px] object-cover shadow-[0_4px_14px_rgba(20,21,28,0.12)]`}
      draggable={false}
    />
  )
}

type LockupProps = {
  compact?: boolean
  light?: boolean
  subtitle?: string
}

export function BrandLockup({ compact = false, light = false, subtitle = 'Lead discovery & outreach' }: LockupProps) {
  return (
    <div className="flex items-center gap-3">
      <BrandMark className={compact ? 'h-9 w-9' : 'h-10 w-10'} />
      <div className="min-w-0">
        <div className={`font-display ${compact ? 'text-[15px]' : 'text-base'} font-extrabold tracking-[-0.02em] ${light ? 'text-white' : 'text-[#14151C]'}`}>
          Lead <span className="text-[#86CF00]">Gen</span>
        </div>
        {subtitle && (
          <div className={`mt-0.5 truncate text-[11px] ${light ? 'text-white/46' : 'text-[#777A87]'}`}>{subtitle}</div>
        )}
      </div>
    </div>
  )
}
