import { BrandMark } from '../components/Brand'

export function AuthLoadingPage({ label = 'Checking your session…' }: { label?: string }) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F7FA] px-4">
      <div className="text-center">
        <div className="relative mx-auto h-14 w-14">
          <BrandMark className="h-14 w-14" alt="" />
          <div className="absolute -inset-1 animate-pulse rounded-[15px] ring-1 ring-[#7B61FF]/16" />
        </div>
        <p className="mt-4 text-sm font-semibold text-[#4B4F5E]">{label}</p>
      </div>
    </main>
  )
}
