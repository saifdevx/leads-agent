import { Icon, type IconName } from '../components/Icon'

type Props = {
  title: string
  description: string
  icon: IconName
  checkpoint: string
  bullets: string[]
}

export function PlaceholderPage({ title, description, icon, checkpoint, bullets }: Props) {
  return (
    <div className="mx-auto max-w-[900px]">
      <section className="card-surface rounded-[14px] p-6 sm:p-8">
        <div className="grid h-11 w-11 place-items-center rounded-[11px] bg-[#F0EDFF] text-[#7B61FF]">
          <Icon name={icon} className="h-5 w-5" />
        </div>
        <h2 className="mt-5 font-display text-[26px] font-bold tracking-[-0.03em] text-[#14151C]">{title}</h2>
        <p className="mt-2 max-w-[650px] text-sm leading-6 text-[#4B4F5E]">{description}</p>

        <div className="mt-7 rounded-[12px] border border-[#E5E3EF] bg-[#FAF9FF] p-5">
          <div className="text-xs font-bold uppercase tracking-[0.1em] text-[#7B61FF]">Planned for {checkpoint}</div>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {bullets.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm leading-5 text-[#4B4F5E]">
                <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#BCE953] ring-2 ring-[#14151C]/5" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  )
}
