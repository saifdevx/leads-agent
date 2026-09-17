import { useState } from 'react'
import { Icon } from '../components/Icon'

type Props = {
  onFoundationAction: (message: string) => void
}

export function FindLeadsPage({ onFoundationAction }: Props) {
  const [advanced, setAdvanced] = useState(false)

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="card-surface rounded-[14px] p-5 sm:p-7 lg:p-8">
        <div className="max-w-[720px]">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#F0EDFF] px-3 py-1.5 text-xs font-bold text-[#6D52EE]">
            <Icon name="spark" className="h-3.5 w-3.5" />
            Free-first lead discovery
          </div>
          <h2 className="font-display text-[28px] font-bold leading-[1.15] tracking-[-0.035em] text-[#14151C] sm:text-[34px]">
            Tell us who you want to find.
          </h2>
          <p className="mt-3 max-w-[610px] text-[15px] leading-7 text-[#4B4F5E]">
            Start simple. The platform will handle search strategy, cleanup, and enrichment behind the scenes as those services are added.
          </p>
        </div>

        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Business or niche</span>
            <input
              className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px] text-[#14151C] placeholder:text-[#9598A4]"
              placeholder="e.g. Solar panel installers"
              defaultValue="Solar panel installers"
            />
          </label>

          <label>
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Location</span>
            <input
              className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px] text-[#14151C] placeholder:text-[#9598A4]"
              placeholder="e.g. Texas, USA"
              defaultValue="Texas, USA"
            />
          </label>

          <label>
            <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Number of leads</span>
            <select defaultValue="100" className="focus-ring h-12 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-4 text-[15px] text-[#14151C]">
              <option>25</option>
              <option>50</option>
              <option>100</option>
              <option>250</option>
              <option>500</option>
            </select>
          </label>
        </div>

        <button
          type="button"
          onClick={() => setAdvanced((value) => !value)}
          className="focus-ring mt-5 flex items-center gap-2 rounded-lg px-1 py-2 text-sm font-semibold text-[#5E46CF] hover:text-[#7B61FF]"
        >
          Advanced options
          <Icon name="chevron" className={`h-4 w-4 transition ${advanced ? 'rotate-90' : ''}`} />
        </button>

        {advanced && (
          <div className="mt-2 rounded-[12px] border border-[#E5E3EF] bg-[#FAF9FF] p-4 sm:p-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <label>
                <span className="mb-2 block text-[12px] font-bold uppercase tracking-[0.07em] text-[#6A6D7B]">Target role</span>
                <input className="focus-ring h-11 w-full rounded-[9px] border border-[#DBD9E7] bg-white px-3.5 text-sm" defaultValue="Owner, Founder, CEO" />
              </label>
              <div>
                <span className="mb-2 block text-[12px] font-bold uppercase tracking-[0.07em] text-[#6A6D7B]">Discovery mode</span>
                <div className="flex h-11 items-center rounded-[9px] border border-[#DBD9E7] bg-white px-3.5 text-sm font-medium text-[#4B4F5E]">Free sources first</div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-7 flex flex-col gap-3 border-t border-[#ECECF1] pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-[480px] text-xs leading-5 text-[#777A87]">
            Checkpoint 3 adds the persistent Turso data foundation. Live lead search stays disabled until the lead-discovery checkpoint.
          </p>
          <button
            onClick={() => onFoundationAction('Lead search is intentionally disabled in v0.3.0. Authentication and the application foundation are working.')}
            className="focus-ring inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-[10px] bg-[#7B61FF] px-5 text-sm font-bold text-white shadow-[0_8px_20px_rgba(123,97,255,0.22)] transition hover:bg-[#6E53F0]"
          >
            Find Leads
            <Icon name="arrow" className="h-4 w-4" />
          </button>
        </div>
      </section>

      <aside className="space-y-4">
        <div className="rounded-[14px] bg-[#14151C] p-5 text-white shadow-[0_12px_28px_rgba(20,21,28,0.12)]">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[#B39CFF]">
            <Icon name="activity" className="h-4 w-4" />
            Product flow
          </div>
          <div className="mt-5 space-y-4">
            {['Find leads', 'Review leads', 'Contact leads'].map((step, index) => (
              <div key={step} className="flex items-center gap-3">
                <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-extrabold ${index === 0 ? 'bg-[#7B61FF] text-white' : 'border border-white/12 bg-white/5 text-white/55'}`}>{index + 1}</div>
                <div className={index === 0 ? 'text-sm font-semibold text-white' : 'text-sm font-medium text-white/55'}>{step}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card-surface rounded-[14px] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.1em] text-[#7B61FF]">Design rule</div>
          <p className="mt-2 text-sm font-semibold leading-6 text-[#2D3039]">Powerful underneath. Simple on the surface.</p>
          <p className="mt-2 text-xs leading-5 text-[#747784]">Provider selection, retries, queues and AI routing will remain background systems unless the user explicitly opens advanced settings.</p>
        </div>
      </aside>
    </div>
  )
}
