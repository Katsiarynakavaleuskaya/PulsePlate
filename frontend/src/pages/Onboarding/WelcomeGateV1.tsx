import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { buttonClasses } from '../../components/ui';
import { canonicalBrand, colors } from '../../styles/tokens';

const membraneBars = [
  colors.gray['50'],
  colors.gray['50'],
  canonicalBrand.blue,
  colors.gray['50'],
  canonicalBrand.green,
  colors.gray['50'],
  colors.gray['50'],
  colors.gray['50'],
  canonicalBrand.blue,
  colors.gray['50'],
  canonicalBrand.green,
  colors.gray['50'],
  colors.gray['50'],
] as const;

const waveformPath =
  'M 0 32 C 18 70, 40 72, 68 40 S 118 18, 142 42 S 194 76, 226 42 S 286 12, 316 46 S 370 88, 406 44 S 470 14, 504 46 S 564 76, 596 44 S 654 18, 686 40 S 742 80, 780 46';

function formatStepLabel(template: string, current: number, total: number): string {
  return template.replace('%d', String(current)).replace('%d', String(total));
}

export default function WelcomeGateV1() {
  const { t } = useTranslation();
  const stepLabel = formatStepLabel(t('onboarding.welcome.stepA11y'), 1, 4);

  return (
    <main
      aria-label="Welcome Gate v1 preview"
      className="min-h-dvh bg-[var(--color-bg)] px-4 py-4 text-[var(--color-text)] sm:px-6 sm:py-6"
    >
      <section
        className="relative mx-auto min-h-[calc(100dvh-2rem)] max-w-[92rem] overflow-hidden border-[3px] border-[var(--pp-navy)] bg-[var(--color-gray-50)] shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
        style={{
          backgroundImage: [
            `linear-gradient(to right, ${colors.gray['200']} 1px, transparent 1px)`,
            `linear-gradient(to bottom, ${colors.gray['200']} 1px, transparent 1px)`,
          ].join(','),
          backgroundSize: '2.75rem 2.75rem',
        }}
      >
        <div className="pointer-events-none absolute inset-5 border border-black/20 sm:inset-6" />
        <div className="pointer-events-none absolute inset-8 border border-black/16 sm:inset-9" />

        <div className="pointer-events-none absolute left-3 top-2 text-[0.65rem] tracking-[0.18em] text-black/26 sm:left-5 sm:top-3">
          [01]
        </div>
        <div className="pointer-events-none absolute right-3 top-2 text-[0.65rem] tracking-[0.18em] text-black/26 sm:right-5 sm:top-3">
          [02]
        </div>
        <div className="pointer-events-none absolute bottom-2 left-3 text-[0.65rem] tracking-[0.18em] text-black/26 sm:bottom-3 sm:left-5">
          [03]
        </div>
        <div className="pointer-events-none absolute bottom-2 right-3 text-[0.65rem] tracking-[0.18em] text-black/26 sm:bottom-3 sm:right-5">
          [04]
        </div>

        <div className="relative flex min-h-[calc(100dvh-2rem)] flex-col px-7 py-7 sm:px-14 sm:py-12">
          <header className="max-w-2xl space-y-4">
            <div className="space-y-2">
              <p className="text-4xl font-bold tracking-[-0.06em] text-[var(--pp-navy)] sm:text-6xl">
                {t('onboarding.welcome.preview.systemTitle')}
              </p>
              <p className="font-serif text-lg text-black/42 sm:text-[2rem]">
                {t('onboarding.welcome.preview.systemSubtitle')}
              </p>
            </div>
            <p className="max-w-xl font-serif text-sm leading-7 text-black/40 sm:text-lg">
              {t('onboarding.welcome.preview.systemBody')}
            </p>
          </header>

          <div className="mt-10 flex flex-1 flex-col gap-10 sm:mt-14 sm:gap-16">
            <div className="flex justify-end">
              <div className="w-full max-w-[24rem] border-[3px] border-[var(--pp-navy)] bg-[rgba(240,244,248,0.85)] p-7 shadow-[0_18px_40px_rgba(15,23,42,0.08)]">
                <div className="flex h-[21rem] items-stretch gap-3 sm:h-[28rem]">
                  {membraneBars.map((color, index) => (
                    <div
                      key={`${color}-${index}`}
                      className="h-full flex-1 border border-black/20"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="px-2 sm:px-6">
              <div className="relative h-28 sm:h-36">
                <div className="absolute inset-x-0 top-1/2 h-px bg-black/18" />
                <svg
                  aria-hidden="true"
                  className="absolute inset-0 h-full w-full"
                  preserveAspectRatio="none"
                  viewBox="0 0 780 96"
                >
                  <path
                    d={waveformPath}
                    fill="none"
                    stroke={canonicalBrand.gold}
                    strokeLinecap="round"
                    strokeWidth="3.5"
                  />
                  <path
                    d={waveformPath}
                    fill="none"
                    stroke={canonicalBrand.navy}
                    strokeLinecap="round"
                    strokeWidth="1.7"
                  />
                </svg>
              </div>
            </div>

            <div className="mt-auto flex flex-col gap-8 pb-4 sm:flex-row sm:items-end sm:justify-between sm:pb-0">
              <div className="space-y-5">
                <div aria-label={stepLabel} className="flex items-center gap-4">
                  {[1, 2, 3, 4].map((step) => {
                    const isActive = step === 1;
                    return (
                      <span
                        key={step}
                        aria-hidden="true"
                        className={[
                          'flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-semibold',
                          isActive
                            ? 'border-[var(--pp-navy)] bg-[var(--pp-navy)] text-white'
                            : 'border-[var(--pp-navy)] bg-transparent text-[var(--pp-navy)]',
                        ].join(' ')}
                      >
                        {step}
                      </span>
                    );
                  })}
                </div>

                <div className="max-w-md space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.26em] text-black/42">
                    {t('onboarding.welcome.preview.gateEyebrow')}
                  </p>
                  <h1 className="text-3xl font-semibold tracking-[-0.05em] text-[var(--pp-navy)] sm:text-4xl">
                    {t('onboarding.welcome.screen1.title')}
                  </h1>
                  <p className="text-base leading-8 text-black/52 sm:text-lg">
                    {t('onboarding.welcome.screen1.body')}
                  </p>
                  <div className="pt-2">
                    <Link to="/setup" className={buttonClasses({ className: 'inline-flex shadow-sm' })}>
                      {t('onboarding.welcome.cta.start')}
                    </Link>
                  </div>
                </div>
              </div>

              <aside className="w-full max-w-md border-[3px] border-[var(--pp-navy)] bg-[rgba(249,250,251,0.82)] p-5 shadow-[0_18px_40px_rgba(15,23,42,0.08)] sm:p-6">
                <div className="space-y-4">
                  <p className="text-2xl font-bold tracking-[-0.05em] text-[var(--pp-navy)]">
                    {t('onboarding.welcome.preview.panelTitle')}
                  </p>
                  <dl className="space-y-3 text-sm text-black/64 sm:text-base">
                    <div className="grid grid-cols-[4.5rem_1fr] gap-3">
                      <dt className="font-medium text-black/54">{t('onboarding.welcome.preview.panelKeyLabel')}</dt>
                      <dd className="font-mono">has_seen_welcome_v1</dd>
                    </div>
                    <div className="grid grid-cols-[4.5rem_1fr] gap-3">
                      <dt className="font-medium text-black/54">{t('onboarding.welcome.preview.panelFlowLabel')}</dt>
                      <dd className="font-mono">Gate → 4 screens → RootTabs()</dd>
                    </div>
                    <div className="grid grid-cols-[4.5rem_1fr] gap-3">
                      <dt className="font-medium text-black/54">{t('onboarding.welcome.preview.panelLocalesLabel')}</dt>
                      <dd className="font-mono">ru · en · es</dd>
                    </div>
                    <div className="grid grid-cols-[4.5rem_1fr] gap-3">
                      <dt className="font-medium text-black/54">{t('onboarding.welcome.preview.panelPolicyLabel')}</dt>
                      <dd className="font-mono">thin client (no BMI math)</dd>
                    </div>
                  </dl>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
