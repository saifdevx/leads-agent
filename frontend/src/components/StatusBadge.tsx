type Props = {
  status: 'loading' | 'online' | 'offline'
}

export function StatusBadge({ status }: Props) {
  const config = {
    loading: { dot: 'bg-[#B39CFF]', text: 'Connecting' },
    online: { dot: 'bg-[#BCE953]', text: 'API connected' },
    offline: { dot: 'bg-[#E56A6A]', text: 'API unavailable' },
  }[status]

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-[#E5E5EB] bg-white px-3 py-1.5 text-xs font-semibold text-[#4B4F5E]">
      <span className={`h-2 w-2 rounded-full ${config.dot}`} />
      {config.text}
    </div>
  )
}
