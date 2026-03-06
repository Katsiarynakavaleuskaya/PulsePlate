import { borderRadius, canonicalBrand, spacing, typography } from '../../styles/tokens';

export const brandFields = [
  { label: 'App Name', value: 'PulsePlate' },
  { label: 'Tagline EN', value: '"Always on your Pulse"' },
  { label: 'Tagline RU', value: '"Держим руку на пульсе"' },
  { label: 'Subtitle', value: 'Nutrition · Body · Lifestyle' },
  { label: 'Framing', value: 'Wellness-lifestyle only — never clinical' },
] as const;

export const moodTokens = ['Minimal', 'Cozy', 'Intelligent', 'Luxury-Clean'] as const;

export const paletteTokens = [
  { name: 'Navy', value: canonicalBrand.navy, variable: '--pp-navy', role: 'Foundation background' },
  { name: 'Blue', value: canonicalBrand.blue, variable: '--pp-blue', role: 'Primary CTA and focus' },
  { name: 'Green', value: canonicalBrand.green, variable: '--pp-green', role: 'Success and positive motion' },
  { name: 'Red', value: canonicalBrand.red, variable: '--pp-red', role: 'Alerts and critical emphasis' },
  { name: 'Gold', value: canonicalBrand.gold, variable: '--pp-gold', role: 'Premium accent and brand detail' },
] as const;

export const typographySamples = [
  {
    label: 'Display',
    fontSize: typography.fontSize['5xl'],
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.tight,
    letterSpacing: '-0.05em',
    sample: 'PulsePlate',
  },
  {
    label: 'Section Title',
    fontSize: typography.fontSize['2xl'],
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.tight,
    letterSpacing: '-0.03em',
    sample: 'Build calm, premium wellness UI',
  },
  {
    label: 'Body',
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.normal,
    lineHeight: typography.lineHeight.relaxed,
    letterSpacing: '0',
    sample: 'Readable, soft, and precise language for everyday guidance.',
  },
  {
    label: 'Caption',
    fontSize: typography.fontSize.xs,
    fontWeight: typography.fontWeight.medium,
    lineHeight: typography.lineHeight.normal,
    letterSpacing: '0.24em',
    sample: 'Token labels and helper text',
  },
] as const;

export const spacingSamples = [
  { label: '4px', value: spacing[1] },
  { label: '8px', value: spacing[2] },
  { label: '12px', value: spacing[3] },
  { label: '16px', value: spacing[4] },
  { label: '24px', value: spacing[6] },
  { label: '32px', value: spacing[8] },
] as const;

export const radiusSamples = [
  { label: '8px', value: borderRadius.lg },
  { label: '12px', value: borderRadius.xl },
  { label: '16px', value: borderRadius['2xl'] },
] as const;

export const platformScreens = [
  { platform: 'Web', screens: ['Web_Home', 'Web_BMI', 'Web_NutritionSetup', 'Web_Plate', 'Web_Progress', 'Web_Profile', 'Web_Paywall', 'Web_Onboarding'] },
  { platform: 'iOS', screens: ['iOS_Home', 'iOS_BMI', 'iOS_Plate', 'iOS_Progress', 'iOS_WeeklyPlan', 'iOS_Profile', 'iOS_Paywall'] },
  { platform: 'Shared', screens: ['Shared_Buttons', 'Shared_Icons', 'Shared_States', 'Shared_Branding'] },
] as const;

export const forbiddenDirections = [
  'Hyper-realistic medical imagery',
  'Cinematic neon / cyberpunk',
  'Futuristic hologram hospital',
  'Gold luxury emblem / crest',
  'Purple gradient glossy blob',
  '3D chrome icon pack',
] as const;

export const governanceLocks = [
  { toneClass: 'bg-[var(--pp-red)]', text: 'EMBLEM_CORE_v1.0_LOCK — icon remains immutable' },
  { toneClass: 'bg-[var(--pp-red)]', text: 'Brand palette lock — use the canonical 5 colors only' },
  { toneClass: 'bg-[var(--pp-blue)]', text: 'tokens.css stays the source of truth for runtime theming' },
  { toneClass: 'bg-[var(--pp-green)]', text: 'Scope lock — optimize Home, BMI, Setup, Plate, Progress, Profile, Paywall' },
] as const;
