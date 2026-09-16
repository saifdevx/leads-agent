export function AuthLoadingPage({ label = 'Checking your session…' }: { label?: string }) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F7FA] px-4">
      <div className="text-center">
        <div className="mx-auto grid h-11 w-11 place-items-center rounded-[12px] bg-[#14151C] text-white">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/25 border-t-[#B39CFF]" />
        </div>
        <p className="mt-4 text-sm font-semibold text-[#4B4F5E]">{label}</p>
      </div>
    </main>
  )
}
