import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
type WelcomeScreen = 1 | 2 | 3;

interface ScreenConfig {
  eyebrow: string;
  title: string;
  body: string;
}

function formatStepLabel(template: string, current: number, total: number): string {
  return template.replace('%d', String(current)).replace('%d', String(total));
}

function StepDots({ current }: { current: WelcomeScreen }): JSX.Element {
  return (
    <div aria-hidden="true" className="flex items-center gap-2">
      {[1, 2, 3].map((step) => (
        <span
          key={step}
          className={[
            'h-2.5 w-2.5 rounded-full transition',
            step === current ? 'bg-[var(--color-primary)]' : 'bg-white/20',
          ].join(' ')}
        />
      ))}
    </div>
  );
}

interface WelcomeGateV1Props {
  initialScreen?: WelcomeScreen;
}

export default function WelcomeGateV1({ initialScreen = 1 }: WelcomeGateV1Props): JSX.Element {
  const { t } = useTranslation();
  const [screen, setScreen] = useState<WelcomeScreen>(initialScreen);

  const screenConfigs: Record<WelcomeScreen, ScreenConfig> = {
    1: {
      eyebrow: t('onboarding.welcome.screen1.eyebrow'),
      title: t('onboarding.welcome.screen1.title'),
      body: t('onboarding.welcome.screen1.body'),
    },
    2: {
      eyebrow: t('onboarding.welcome.screen2.eyebrow'),
      title: t('onboarding.welcome.screen2.title'),
      body: t('onboarding.welcome.screen2.body'),
    },
    3: {
      eyebrow: t('onboarding.welcome.screen3.eyebrow'),
      title: t('onboarding.welcome.screen3.title'),
      body: t('onboarding.welcome.screen3.body'),
    },
  };

  const stepLabel = formatStepLabel(t('onboarding.welcome.stepA11y'), screen, 3);
  const currentScreen = screenConfigs[screen];

  return (
    <main
      aria-label="Welcome Gate v1 preview"
      className="min-h-dvh bg-[#0d0d1a] px-4 py-6 text-white sm:px-6"
    >
      <section className="mx-auto flex min-h-[calc(100dvh-3rem)] max-w-[24rem] flex-col rounded-[2rem] bg-[#0f172a] p-6 shadow-[0_30px_70px_rgba(0,0,0,0.35)]">
        {screen === 1 ? (
          <>
            <div className="flex justify-end">
              <button type="button" className="text-sm text-white/55">
                {t('onboarding.welcome.skip')}
              </button>
            </div>

            <div className="mt-6 flex flex-col items-center text-center">
              <div className="relative flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-full bg-[var(--color-primary)]">
                <div className="absolute inset-[-0.6rem] rounded-full bg-[var(--color-primary)]/20 blur-xl" />
                <div className="relative h-[4.5rem] w-[4.5rem] rounded-full bg-[var(--color-primary)]" />
              </div>
              <p className="mt-6 text-lg text-white/90">{currentScreen.eyebrow}</p>
              <h1 className="mt-3 text-[2.25rem] font-medium leading-[1.08] tracking-[-0.05em] text-white">
                {currentScreen.title}
              </h1>
            </div>

            <div className="mt-14 grid grid-cols-3 text-center text-sm text-white/84">
              <span>{t('onboarding.welcome.screen1.tabs.bmi')}</span>
              <span>{t('onboarding.welcome.screen1.tabs.plate')}</span>
              <span>{t('onboarding.welcome.screen1.tabs.plans')}</span>
            </div>

            <div className="mt-8 rounded-[1.25rem] border border-white/12 bg-white/[0.06] p-5">
              <p className="text-base text-white">{t('onboarding.welcome.screen1.cardTitle')}</p>
              <ul className="mt-4 space-y-3 text-[1rem] text-white/75">
                {[1, 2, 3].map((item) => (
                  <li key={item}>{t(`onboarding.welcome.screen1.points.${item}`)}</li>
                ))}
              </ul>
            </div>

            <p className="mt-6 text-center text-sm text-white/36">{t('onboarding.welcome.screen1.footer')}</p>

            <div className="mt-auto space-y-6 pt-8">
              <div aria-label={stepLabel} className="flex justify-center">
                <StepDots current={screen} />
              </div>
              <button
                type="button"
                className="w-full rounded-full bg-[var(--color-primary)] px-6 py-4 text-lg font-semibold text-white"
                onClick={() => setScreen(2)}
              >
                {t('onboarding.welcome.cta.start')}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <button
                type="button"
                className="text-sm text-white/55"
                onClick={() => setScreen((prev) => (prev === 3 ? 2 : 1))}
              >
                {t('onboarding.welcome.back')}
              </button>
              <div aria-label={stepLabel}>
                <StepDots current={screen} />
              </div>
            </div>

            <div className="mt-16">
              <p className="text-sm text-white/42">{currentScreen.eyebrow}</p>
              <h1 className="mt-4 text-[2.1rem] font-semibold leading-[1.08] tracking-[-0.05em] text-white">
                {currentScreen.title}
              </h1>
              <p className="mt-4 text-base leading-7 text-white/68">{currentScreen.body}</p>
            </div>

            {screen === 2 ? (
              <div className="mt-14 space-y-6">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] p-4">
                    <p className="text-base font-semibold text-white">
                      {t(`onboarding.welcome.screen2.steps.${item}.title`)}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/62">
                      {t(`onboarding.welcome.screen2.steps.${item}.body`)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-10 rounded-[1.25rem] border border-white/10 bg-white/[0.06] p-4">
                <div className="space-y-4">
                  {[1, 2, 3, 4].map((goal) => (
                    <button
                      key={goal}
                      type="button"
                      className={[
                        'flex w-full items-center rounded-2xl border px-4 py-4 text-left text-base transition',
                        goal === 1
                          ? 'border-white/25 bg-white/[0.08] text-white'
                          : 'border-transparent bg-transparent text-white/82 hover:bg-white/[0.04]',
                      ].join(' ')}
                    >
                      {t(`onboarding.welcome.screen3.goals.${goal}`)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-auto pt-10">
              {screen === 2 ? (
                <button
                  type="button"
                  className="w-full rounded-2xl bg-[#43c6cf] px-6 py-4 text-lg font-semibold text-[#08111f]"
                  onClick={() => setScreen(3)}
                >
                  {t('onboarding.welcome.cta.continue')}
                </button>
              ) : (
                <Link
                  to="/setup"
                  className="flex w-full items-center justify-center rounded-2xl bg-[#43c6cf] px-6 py-4 text-lg font-semibold text-[#08111f]"
                >
                  {t('onboarding.welcome.cta.finish')}
                </Link>
              )}
            </div>
          </>
        )}
      </section>

      <section className="mx-auto mt-6 max-w-[24rem] rounded-[1.5rem] border border-white/8 bg-white/[0.04] p-4 text-sm text-white/52">
        <p className="font-semibold uppercase tracking-[0.18em] text-white/38">{t('onboarding.welcome.preview.panelTitle')}</p>
        <div className="mt-3 space-y-2">
          <p>
            {t('onboarding.welcome.preview.panelFlowLabel')} Gate → screens 1-3 preview → setup
          </p>
          <p>
            {t('onboarding.welcome.preview.panelLocalesLabel')} ru · en · es
          </p>
          <p>
            {t('onboarding.welcome.preview.panelPolicyLabel')} preview only, no persistence
          </p>
        </div>
      </section>
    </main>
  );
}
