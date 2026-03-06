import { FitChefMascot, PulsePlateLogo } from '../brand';
import { brandFields, moodTokens } from './data';
import { PanelShell } from './shared';

export function BrandIdentityPanel() {
  return (
    <PanelShell title="Identity Fields" subtitle="Canonical copy and framing">
      <dl className="space-y-3">
        {brandFields.map((field) => (
          <div
            key={field.label}
            className="grid gap-1 border-b border-white/6 pb-3 last:border-b-0 last:pb-0 sm:grid-cols-[96px_minmax(0,1fr)]"
          >
            <dt className="font-mono text-[11px] uppercase tracking-[0.16em] text-white/34">{field.label}</dt>
            <dd className="text-sm text-white">{field.value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-5 flex flex-wrap gap-2">
        {moodTokens.map((token) => (
          <span
            key={token}
            className="rounded-md bg-[rgba(212,175,55,0.12)] px-2.5 py-1.5 text-xs font-medium text-[var(--pp-gold)]"
          >
            {token}
          </span>
        ))}
      </div>
    </PanelShell>
  );
}

export function LogoVariantsPanel() {
  return (
    <PanelShell title="Logo Variants" subtitle="Brand mark, lockup, mascot, and compact usage">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/12 bg-[var(--pp-navy)] p-4">
            <PulsePlateLogo variant="lockup" />
            <p className="mt-3 text-xs text-white/55">Dark surface lockup</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <PulsePlateLogo tone="light" variant="lockup" />
            <p className="mt-3 text-xs text-slate-500">Light surface lockup</p>
          </div>
          <div className="rounded-2xl border border-white/12 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center gap-4">
              <PulsePlateLogo variant="mark" />
              <PulsePlateLogo variant="compact" />
            </div>
            <p className="mt-3 text-xs text-white/55">Canonical mark + compact lockup</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1">
          <div className="rounded-2xl border border-white/12 bg-white/[0.03] p-4">
            <FitChefMascot className="mx-auto" size="md" variant="static" />
            <p className="mt-3 text-center text-xs text-white/55">FitChef static</p>
          </div>
          <div className="rounded-2xl border border-white/12 bg-white/[0.03] p-4">
            <FitChefMascot className="mx-auto" size="md" variant="wink" />
            <p className="mt-3 text-center text-xs text-white/55">FitChef wink</p>
          </div>
        </div>
      </div>
    </PanelShell>
  );
}
