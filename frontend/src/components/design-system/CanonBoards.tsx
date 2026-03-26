import type { ReactNode } from 'react';
import fitchefOnboardingWelcome from '../../assets/brand/fitchef-onboarding-welcome-v1.png';
import { canonicalBrand, colors, spacing } from '../../styles/tokens';
import { FitChefMascot, PulsePlateLogo } from '../brand';
import { buttonClasses } from '../ui';
import { OverviewHeader, PanelShell } from './shared';

const designSystemCanvasRgb = '26 31 46';

const brandPalette = [
  { label: 'PP/Brand/Navy', value: canonicalBrand.navy },
  { label: 'PP/Brand/Blue', value: canonicalBrand.blue },
  { label: 'PP/Brand/Green', value: canonicalBrand.green },
  { label: 'PP/Brand/Red', value: canonicalBrand.red, note: 'accent only' },
] as const;

const semanticPalette = [
  { label: 'PP/Semantic/Primary', value: canonicalBrand.blue },
  { label: 'PP/Semantic/Text', value: canonicalBrand.navy },
  { label: 'PP/Semantic/Success', value: canonicalBrand.green },
  { label: 'PP/Semantic/Error', value: canonicalBrand.red },
  { label: 'PP/Semantic/Info', value: canonicalBrand.blue },
  { label: 'PP/Semantic/Focus', value: canonicalBrand.blue },
] as const;

const largeTitlePointSize = 3 * 10;

const typeScale = [
  'PP/iOS/Type/Caption — 12 Regular',
  'PP/iOS/Type/BodyStrong — 16 SemiBold',
  'PP/iOS/Type/Title — 18 SemiBold',
  'PP/iOS/Type/Heading — 24 Bold',
  `PP/iOS/Type/LargeTitle — ${largeTitlePointSize} Bold`,
] as const;

const spacingScale = [
  `PP/Spacing/xs — ${spacing[1]}`,
  `PP/Spacing/sm — ${spacing[2]}`,
  `PP/Spacing/md — ${spacing[4]}`,
  `PP/Spacing/lg — ${spacing[6]}`,
  `PP/Spacing/xl — ${spacing[8]}`,
  `PP/Spacing/2xl — ${spacing[12]}`,
] as const;

const radiusScale = [
  'PP/Radius/none — 0px',
  'PP/Radius/sm — 4px',
  'PP/Radius/md — 8px',
  'PP/Radius/lg — 12px',
  'PP/Radius/xl — 16px',
  'PP/Radius/xxl — 18px',
  'PP/Radius/full — 999px',
] as const;

const shadowScale = [
  'PP/Shadow/card — 0 2px 8px rgba(0,0,0,0.12)',
  'PP/Shadow/modal — 0 8px 24px rgba(0,0,0,0.20)',
  'PP/Shadow/overlay — 0 16px 48px rgba(0,0,0,0.30)',
] as const;

const motionScale = [
  'PP/Motion/duration-xs — 100ms',
  'PP/Motion/duration-sm — 200ms',
  'PP/Motion/duration-md — 300ms',
  'PP/Motion/duration-lg — 500ms',
  'PP/Motion/easing-default — ease-in-out',
  'PP/Motion/easing-spring — spring(1, 100, 10, 0)',
] as const;

const tabMappings = [
  { label: 'Home', icon: 'house' },
  { label: 'BMI', icon: 'scalemass' },
  { label: 'Plate', icon: 'fork.knife' },
  { label: 'Progress', icon: 'chart.line' },
  { label: 'Week', icon: 'calendar' },
  { label: 'Profile', icon: 'person' },
] as const;

const updateCards = [
  {
    title: 'GlassCard (iOS)',
    tone: 'rgba(212, 175, 55, 0.18)',
    toneText: 'var(--pp-gold)',
    body:
      'cornerRadius: 18px, fill white at 8%, border white at 12%, blur 24px, and a reduced-transparency fallback.',
  },
  {
    title: 'MascotBubble',
    tone: 'rgba(51, 159, 255, 0.18)',
    toneText: 'var(--color-primary)',
    body:
      'Use a 48×48 icon container with 12px radius. Keep it square and lightweight; do not switch to a circular avatar.',
  },
  {
    title: 'VipBadge (governance)',
    tone: 'rgba(255, 93, 93, 0.18)',
    toneText: 'var(--color-error)',
    body:
      'Purple gradients stay blocked. The approved fallback remains navy-to-gold or a solid gold treatment only.',
  },
] as const;

const portraitVariants = [
  { label: 'Neutral', variant: 'neutral' as const },
  { label: 'Wink', variant: 'wink' as const },
  { label: 'Thinking', variant: 'thinking' as const },
  { label: 'Sleepy', variant: 'sleepy' as const },
  { label: 'Surprised', variant: 'surprised' as const },
] as const;

const holdCandidates = [
  'Profile Setup',
  'Track Progress',
  'Build Meal Plan',
  'Shopping List',
  'Healthy Choice',
  'Hydration / Workout',
] as const;

function formatHex(value: string): string {
  return value.toUpperCase();
}

function PaletteSwatch({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-[18px] border border-white/12 bg-white/[0.03] p-3">
      <div
        className="h-20 rounded-xl border border-white/30"
        style={{ backgroundColor: value }}
      />
      <p className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-white/80">{label}</p>
      <p className="mt-2 text-xs text-white/60">{formatHex(value)}</p>
      {note ? <p className="mt-1 text-[11px] text-white/42">{note}</p> : null}
    </div>
  );
}

function PanelList({
  title,
  items,
  footer,
}: {
  title: string;
  items: readonly string[];
  footer?: string;
}) {
  return (
    <div className="rounded-[20px] border border-white/8 bg-white/[0.03] p-4">
      <p className="text-sm font-semibold text-white">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <p key={item} className="text-xs leading-5 text-white/65">
            {item}
          </p>
        ))}
      </div>
      {footer ? <p className="mt-3 text-[11px] text-white/42">{footer}</p> : null}
    </div>
  );
}

interface BrandAssetPlaceholderProps {
  className?: string;
}

export function BrandAssetPlaceholder({
  className = '',
}: BrandAssetPlaceholderProps) {
  return (
    <div
      aria-hidden="true"
      className={['rounded-[10px] bg-[rgba(217,217,217,1)]', className].join(' ').trim()}
      data-name="SLOT_Portrait_Neutral"
      data-node-id="86:2"
    />
  );
}

function CanonSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-5">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white/80">{title}</p>
      {children}
    </section>
  );
}

function PortraitTile({
  label,
  variant,
}: {
  label: string;
  variant: 'neutral' | 'wink' | 'thinking' | 'sleepy' | 'surprised';
}) {
  return (
    <div className="space-y-3">
      <div className="rounded-[18px] border border-dashed border-white/20 bg-[rgba(255,255,255,0.02)] p-3">
        <FitChefMascot className="h-[132px] w-full" size="md" variant={variant} />
      </div>
      <p className="text-center text-xs text-white/54">{label}</p>
    </div>
  );
}

function HoldCandidateTile({ label }: { label: string }) {
  return (
    <div className="space-y-3">
      <div className="rounded-[18px] border border-dashed border-white/20 bg-[rgba(255,255,255,0.02)] p-4">
        <BrandAssetPlaceholder className="h-[132px] w-full" />
      </div>
      <p className="text-center text-xs text-white/54">{label}</p>
    </div>
  );
}

export function IOSFoundationTokensBoard() {
  return (
    <PanelShell
      className="border-white/10 bg-[rgba(255,255,255,0.04)] shadow-[0_30px_80px_rgba(0,0,0,0.28)]"
      subtitle="Figma node 35:148 translated into the repo-native Storybook review surface."
      title="PP iOS Foundation Tokens v1"
    >
      <div className="space-y-6">
        <div className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
          <div className="space-y-6">
            <div>
              <p className="text-sm font-semibold text-white">Brand palette</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {brandPalette.map((token) => (
                  <PaletteSwatch key={token.label} label={token.label} note={token.note} value={token.value} />
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold text-white">Semantic colors</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {semanticPalette.map((token) => (
                  <PaletteSwatch key={token.label} label={token.label} value={token.value} />
                ))}
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <PanelList title="iOS type scale" items={typeScale} />
              <PanelList title="Spacing" items={spacingScale} />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <PanelList
                footer="PP/Radius/xxl remains a component delta for the glass-card family."
                title="Border Radius"
                items={radiusScale}
              />
              <PanelList title="Shadows / Elevation" items={shadowScale} />
            </div>
          </div>

          <div className="space-y-4">
            <PanelList title="Motion and reduced-motion notes" items={motionScale} />
            <PanelList
              title="Cross-surface token mapping"
              items={[
                'Web token source: tokens.css / tokens.ts',
                'iOS token source: Assets.xcassets + Color+Assets.swift',
                'Semantic tokens stay mapped to the brand palette instead of ad-hoc color picks.',
              ]}
            />
            <div className="rounded-[20px] border border-white/8 bg-white/[0.03] p-4">
              <p className="text-sm font-semibold text-white">CI / Sora palette aliases</p>
              <p className="mt-2 text-xs leading-5 text-white/58">
                Alias colors stay documentation-only. Runtime theming remains anchored to the canonical brand tokens.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <PaletteSwatch label="PP/CI/Navy" value={colors.navy['900']} />
                <PaletteSwatch label="PP/CI/Blue" value={colors.blue['500']} />
                <PaletteSwatch label="PP/CI/Red" value={colors.heart['500']} />
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-[22px] bg-white p-5 text-[var(--color-text)] shadow-[0_22px_54px_rgba(15,23,42,0.18)]">
          <p className="text-sm font-semibold">PPButton sizes — align variants</p>
          <p className="mt-2 text-xs text-slate-500">sm: 40px · md: 44px · lg: 48px</p>
          <div className="mt-4 flex flex-wrap gap-4">
            <button className={buttonClasses({ size: 'sm' })} type="button">sm 40</button>
            <button className={buttonClasses({ size: 'md' })} type="button">md 44</button>
            <button className={buttonClasses({ size: 'lg' })} type="button">lg 48</button>
          </div>
        </div>

        <div className="rounded-[22px] bg-white p-5 text-[var(--color-text)] shadow-[0_22px_54px_rgba(15,23,42,0.18)]">
          <p className="text-sm font-semibold">RootTabs mapping — 6 tabs (iOS)</p>
          <p className="mt-2 text-xs text-slate-500">Reference icons stay aligned to the iOS design-system naming.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {tabMappings.map((tab) => (
              <div
                key={tab.label}
                className="rounded-[14px] border border-slate-200 bg-slate-50 px-4 py-3"
              >
                <p className="text-sm font-semibold text-slate-900">{tab.label}</p>
                <p className="mt-1 text-xs text-slate-500">{tab.icon}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          {updateCards.map((card) => (
            <div
              key={card.title}
              className="rounded-[18px] border border-white/8 bg-white/[0.03] p-4"
            >
              <span
                className="inline-flex rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em]"
                style={{ backgroundColor: card.tone, color: card.toneText }}
              >
                Update
              </span>
              <p className="mt-4 text-sm font-semibold text-white">{card.title}</p>
              <p className="mt-3 text-xs leading-5 text-white/60">{card.body}</p>
            </div>
          ))}
        </div>
      </div>
    </PanelShell>
  );
}

export function BrandCanonBoard() {
  return (
    <PanelShell
      className="border-white/10 bg-[rgba(255,255,255,0.04)] shadow-[0_30px_80px_rgba(0,0,0,0.28)]"
      subtitle="Figma node 61:77 translated into canonical brand-governance surfaces for Storybook."
      title="PP Brand + FitChef Logo Canon v1"
    >
      <div
        className="rounded-[28px] p-5 sm:p-6"
        style={{ backgroundColor: `rgb(${designSystemCanvasRgb})` }}
      >
        <div className="grid gap-8 xl:grid-cols-5 xl:gap-10">
          <CanonSection title="01 — Emblem / Logo Canon">
            <p className="max-w-sm text-sm leading-6 text-white/62">
              The emblem stays locked to the core PulsePlate geometry. Do not recolor it, stretch it, or place it on a
              noisy background.
            </p>
            <div className="rounded-[18px] bg-[var(--pp-navy)] p-5">
              <div className="mx-auto max-w-[260px]">
                <PulsePlateLogo className="h-auto w-full" variant="mark" />
              </div>
            </div>
          </CanonSection>

          <CanonSection title="02 — Locked FitChef Core Portraits">
            <p className="max-w-sm text-sm leading-6 text-white/62">
              Neutral, wink, thinking, sleepy, and surprised are the approved core expressions for documentation and
              onboarding-adjacent surfaces.
            </p>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-2 2xl:grid-cols-3">
              {portraitVariants.map((portrait) => (
                <PortraitTile key={portrait.label} label={portrait.label} variant={portrait.variant} />
              ))}
            </div>
          </CanonSection>

          <CanonSection title="03 — Locked FitChef Onboarding Scene">
            <p className="max-w-sm text-sm leading-6 text-white/62">
              Use the welcome scene as a single onboarding illustration. Keep it on quiet navy or white surfaces only.
            </p>
            <div className="rounded-[18px] bg-[var(--pp-navy)] p-4">
              <img
                alt="FitChef onboarding welcome scene"
                className="mx-auto h-auto w-full max-w-[260px] object-contain"
                src={fitchefOnboardingWelcome}
              />
            </div>
            <p className="text-center text-xs text-white/54">Onboarding Welcome</p>
          </CanonSection>

          <CanonSection title="04 — Candidate Extensions / Hold">
            <p className="max-w-sm text-sm leading-6 text-white/62">
              These slots stay in a hold lane until the brand lead explicitly approves new scenes, co-brands, or
              seasonal variants.
            </p>
            <div className="grid grid-cols-2 gap-4">
              {holdCandidates.map((candidate) => (
                <HoldCandidateTile key={candidate} label={candidate} />
              ))}
            </div>
          </CanonSection>

          <CanonSection title="05 — Usage Rules">
            <ol className="space-y-3 text-sm leading-6 text-white/62">
              <li>1. Use the mark on white or the core navy canvas only.</li>
              <li>2. Keep at least one emblem-height of clear space around the mark.</li>
              <li>3. Do not rotate, stretch, bevel, or shadow the emblem.</li>
              <li>4. Avoid busy photography behind the mark.</li>
              <li>5. Reserve green for CTA emphasis only, never for the emblem itself.</li>
              <li>6. Portrait expressions stay illustrative context, not navigation icons.</li>
            </ol>
          </CanonSection>
        </div>
      </div>
    </PanelShell>
  );
}

export function CanonBoardsSection() {
  return (
    <section className="mt-10">
      <OverviewHeader
        description="High-fidelity Figma documentation boards converted into repo-native React review surfaces for tokens, mascot canon, and brand governance."
        eyebrow="5. Canon Boards"
        title="Figma documentation boards with runtime-safe assets"
      />
      <div className="grid gap-6">
        <IOSFoundationTokensBoard />
        <BrandCanonBoard />
      </div>
    </section>
  );
}
