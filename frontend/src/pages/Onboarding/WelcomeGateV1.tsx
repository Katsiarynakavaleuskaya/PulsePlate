import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import fitchefOnboardingWelcome from '../../assets/brand/fitchef-onboarding-welcome-v1.png';
import { PulsePlateLogo } from '../../components/brand';
import {
  WELCOME_GATE_V1_FEATURE_POINT_IDS,
  WELCOME_GATE_V1_PREVIEW_LOCALES,
  WELCOME_GATE_V1_PREVIEW_STEP,
  WELCOME_GATE_V1_PREVIEW_STEP_COUNT,
  WELCOME_GATE_V1_SETUP_TARGET,
} from './welcomeGateV1Policy';

function StepIndicator({ label }: { label: string }): JSX.Element {
  return (
    <div className="inline-flex items-center gap-3">
      <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-[var(--pp-green)]" />
      <span className="text-sm text-white/52">{label}</span>
    </div>
  );
}

export default function WelcomeGateV1(): JSX.Element {
  const { t } = useTranslation();
  const stepLabel = t('onboarding.welcome.stepA11y', {
    current: WELCOME_GATE_V1_PREVIEW_STEP,
    total: WELCOME_GATE_V1_PREVIEW_STEP_COUNT,
  });

  return (
    <main
      aria-label={t('onboarding.welcome.mainA11y')}
      className="min-h-dvh bg-[radial-gradient(circle_at_top,rgba(51,159,255,0.18),transparent_38%),var(--pp-navy)] px-4 py-6 text-white sm:px-6"
    >
      <section className="mx-auto grid min-h-[calc(100dvh-3rem)] max-w-5xl gap-6 rounded-[2rem] border border-white/10 bg-[rgba(20,24,38,0.86)] p-5 shadow-[0_30px_70px_rgba(0,0,0,0.35)] sm:p-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)] lg:gap-8">
        <div className="flex flex-col rounded-[1.7rem] border border-white/8 bg-white/[0.04] p-6 sm:p-7">
          <div className="flex items-center justify-between gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-white/50">
              <span className="h-2 w-2 rounded-full bg-[var(--pp-green)]" />
              {t('onboarding.welcome.routeMirrorBadge')}
            </div>
            <Link to={WELCOME_GATE_V1_SETUP_TARGET} className="text-sm text-white/55 transition hover:text-white/78">
              {t('onboarding.welcome.skip')}
            </Link>
          </div>

          <div className="mt-8">
            <PulsePlateLogo className="h-auto w-[11.5rem]" variant="lockup" />
            <p className="mt-8 text-sm uppercase tracking-[0.24em] text-white/42">
              {t('onboarding.welcome.screen1.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-xl text-[2.9rem] font-semibold leading-[0.98] tracking-[-0.06em] text-white sm:text-[3.4rem]">
              {t('onboarding.welcome.screen1.title')}
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-white/68">{t('onboarding.welcome.screen1.body')}</p>
          </div>

          <div className="mt-10 rounded-[1.4rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/48">
              {t('onboarding.welcome.screen1.cardTitle')}
            </p>
            <ul className="mt-4 space-y-3 text-base leading-7 text-white/78">
              {WELCOME_GATE_V1_FEATURE_POINT_IDS.map((item) => (
                <li key={item}>{t(`onboarding.welcome.screen1.points.${item}`)}</li>
              ))}
            </ul>
          </div>

          <p className="mt-6 text-sm text-white/40">{t('onboarding.welcome.screen1.footer')}</p>

          <div className="mt-auto flex flex-col gap-4 pt-8 sm:flex-row sm:items-center sm:justify-between">
            <StepIndicator label={stepLabel} />
            <Link
              to={WELCOME_GATE_V1_SETUP_TARGET}
              className="inline-flex items-center justify-center rounded-full bg-[var(--pp-green)] px-7 py-4 text-lg font-semibold text-[var(--pp-navy)] transition hover:brightness-105"
            >
              {t('onboarding.welcome.cta.start')}
            </Link>
          </div>
        </div>

        <div className="flex flex-col gap-6">
          <div className="relative overflow-hidden rounded-[1.8rem] border border-white/10 bg-[linear-gradient(180deg,rgba(51,159,255,0.14),rgba(255,255,255,0.03))] p-4 sm:p-5">
            <div className="absolute inset-x-0 top-0 h-px bg-white/12" />
            <img
              alt={t('onboarding.welcome.heroAlt')}
              className="h-full w-full rounded-[1.35rem] object-cover"
              src={fitchefOnboardingWelcome}
            />
          </div>

          <section className="rounded-[1.5rem] border border-white/8 bg-white/[0.04] p-4 text-sm text-white/52">
            <p className="font-semibold uppercase tracking-[0.18em] text-white/38">
              {t('onboarding.welcome.preview.panelTitle')}
            </p>
            <div className="mt-3 space-y-2">
              <p>
                {t('onboarding.welcome.preview.panelFlowLabel')} {t('onboarding.welcome.preview.panelFlowValue')}
              </p>
              <p>
                {t('onboarding.welcome.preview.panelTargetLabel')} {t('onboarding.welcome.preview.panelTargetValue')}
              </p>
              <p>
                {t('onboarding.welcome.preview.panelLocalesLabel')} {WELCOME_GATE_V1_PREVIEW_LOCALES.join(' / ')}
              </p>
              <p>
                {t('onboarding.welcome.preview.panelPolicyLabel')} {t('onboarding.welcome.preview.panelPolicyValue')}
              </p>
              <p>
                {t('onboarding.welcome.preview.panelBlockedLabel')} {t('onboarding.welcome.preview.panelBlockedValue')}
              </p>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
