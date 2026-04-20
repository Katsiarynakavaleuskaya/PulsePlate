import { Activity, ChartColumnBig, Home, ShieldCheck, Sparkles, UtensilsCrossed } from 'lucide-react';
import { MarketingCard, MarketingSection, SectionHeader, StatusPill } from './MarketingPrimitives';

const surfaces = [
  {
    title: 'Home',
    description:
      'Your calm dashboard overview. See session status, quick actions, and navigate to all product surfaces from one structured entry point.',
    supporting: 'Dashboard & navigation',
    icon: Home,
  },
  {
    title: 'Setup',
    description:
      'Define your core nutrition inputs and preferences. Structured preparation to help PulsePlate guide you more clearly.',
    supporting: 'Configuration & preparation',
    icon: ShieldCheck,
  },
  {
    title: 'Plate',
    description:
      'Your main daily nutrition surface. Plan and structure your meals with calm clarity and simple focus.',
    supporting: 'Daily nutrition planning',
    icon: UtensilsCrossed,
  },
  {
    title: 'Progress',
    description:
      'Review trends and signals over time. See patterns and stay oriented without over-analysis.',
    supporting: 'Trends & understanding',
    icon: ChartColumnBig,
  },
  {
    title: 'BMI',
    description:
      'Understand your baseline metrics with wellness-focused clarity. A practical starting point for self-awareness.',
    supporting: 'Baseline metrics',
    icon: Activity,
  },
  {
    title: 'Pro',
    description:
      'Unlock deeper guidance and structure. Access AI coaching, weekly insights, and more personalized support where available.',
    supporting: 'Premium guidance & tools',
    icon: Sparkles,
    pillTone: 'premium',
  },
];

export function CoreSurfacesSection() {
  return (
    <MarketingSection id="core-surfaces">
      <SectionHeader
        description="The public site stays honest about the real product map: six clear surfaces, one calm navigation logic."
        eyebrow="Product surfaces"
        title="Inside PulsePlate"
      />

      <div className="ppm-surfaces-grid" style={{ marginTop: '2.5rem' }}>
        {surfaces.map(({ title, description, supporting, icon: Icon, pillTone }) => (
          <MarketingCard key={title} className="ppm-surface-card">
            <div className="ppm-surface-top">
              <div className="ppm-icon-box">
                <Icon size={20} />
              </div>
              <StatusPill
                className={pillTone === 'premium' ? 'ppm-pill--premium' : 'ppm-pill--success'}
              >
                {pillTone === 'premium' ? 'Pro' : 'Available now'}
              </StatusPill>
            </div>
            <h3 className="ppm-surface-title" style={{ marginTop: '1.5rem' }}>
              {title}
            </h3>
            <p className="ppm-surface-copy">{description}</p>
            <p className="ppm-surface-support" style={{ marginTop: '1.25rem' }}>
              {supporting}
            </p>
          </MarketingCard>
        ))}
      </div>
    </MarketingSection>
  );
}

export default CoreSurfacesSection;
