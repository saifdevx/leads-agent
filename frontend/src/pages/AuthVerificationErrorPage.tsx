type Props = {
  message: string
  onRetry: () => void
  onSignOut: () => void
}

export function AuthVerificationErrorPage({ message, onRetry, onSignOut }: Props) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F7FA] px-4 py-10">
      <section className="card-surface w-full max-w-[560px] rounded-[16px] p-6 sm:p-8">
        <div className="text-xs font-bold uppercase tracking-[0.11em] text-[#7B61FF]">Backend authentication</div>
        <h1 className="mt-2 font-display text-2xl font-bold tracking-[-0.025em] text-[#14151C]">We could not verify this session</h1>
        <p className="mt-3 text-sm leading-6 text-[#5A5D69]">{message}</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button onClick={onRetry} className="focus-ring h-11 rounded-[10px] bg-[#7B61FF] px-5 text-sm font-bold text-white hover:bg-[#6E53F0]">Try again</button>
          <button onClick={onSignOut} className="focus-ring h-11 rounded-[10px] border border-[#DCDDE5] bg-white px-5 text-sm font-semibold text-[#353841] hover:bg-[#FAFAFC]">Sign out</button>
        </div>
      </section>
    </main>
  )
}
