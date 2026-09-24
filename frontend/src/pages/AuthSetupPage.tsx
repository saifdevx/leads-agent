import { BrandLockup } from '../components/Brand'

export function AuthSetupPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F7FA] px-4 py-10">
      <section className="card-surface w-full max-w-[640px] rounded-[18px] p-6 sm:p-8">
        <BrandLockup subtitle="Setup required" />
        <div className="mt-6 text-xs font-bold uppercase tracking-[0.11em] text-[#7B61FF]">Firebase setup</div>
        <h1 className="mt-1 font-display text-xl font-bold text-[#14151C]">Firebase configuration is required</h1>

        <p className="mt-5 text-sm leading-6 text-[#5A5D69]">Copy <code className="rounded bg-[#F0EDFF] px-1.5 py-0.5 text-[#6048D3]">frontend/.env.example</code> to <code className="rounded bg-[#F0EDFF] px-1.5 py-0.5 text-[#6048D3]">frontend/.env</code> and add the Firebase web-app values from your Firebase project.</p>

        <div className="mt-5 rounded-[12px] border border-[#E3E1EC] bg-[#FAF9FF] p-4 font-mono text-xs leading-6 text-[#454854]">
          <div>VITE_FIREBASE_API_KEY=</div>
          <div>VITE_FIREBASE_AUTH_DOMAIN=</div>
          <div>VITE_FIREBASE_PROJECT_ID=</div>
          <div>VITE_FIREBASE_APP_ID=</div>
        </div>

        <p className="mt-4 text-xs leading-5 text-[#777A87]">After saving the values, restart <strong>npm run dev</strong>. Do not put the Firebase Admin service-account private key in the frontend.</p>
      </section>
    </main>
  )
}
