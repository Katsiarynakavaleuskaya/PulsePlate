import { Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import {
  MarketingCard,
  MarketingSection,
  SectionHeader,
  StatusPill,
  marketingButtonClasses,
} from './MarketingPrimitives';

const tiers = [
  {
    name: 'Free',
    positioning: 'Understand the basics',
    description:
      'Use the core planning surfaces and baseline context before deciding whether you need more depth.',
    items: [
      'Access Home dashboard',
      'Complete Setup',
      'Use BMI calculator',
      'Review basic Progress',
      'Understand your baseline metrics',
    ],
    label: 'Available now',
    ctaLabel: 'Start with Free',
    ctaTo: '/setup',
    ctaClass: marketingButtonClasses.secondary,
  },
  {
    name: 'Pro',
    positioning: 'Plan with more confidence',
    description:
      'Add more structure to everyday wellness planning with guided prompts and deeper progress context.',
    items: [
      'Everything in Free',
      'Guided wellness prompts',
      'Deeper Progress views',
      'Weekly insights',
      'Open Plate with more structure',
      'More product depth',
    ],
    label: 'Available now',
    ctaLabel: 'Explore Pro',
    ctaTo: '/pro',
    ctaClass: marketingButtonClasses.primary,
    featured: true,
  },
  {
    name: 'VIP',
    positioning: 'More personalized support and automation where available',
    description:
      'A preview lane for expanded personalization and automation when those surfaces are release-ready.',
    items: [
      'Everything in Pro',
      'More personalized wellness guidance',
      'Expanded automation where available',
      'Priority support access',
      'Early access to new features',
    ],
    label: 'Preview',
    ctaLabel: 'Continue to next steps',
    ctaTo: '#final-cta',
    ctaClass: marketingButtonClasses.secondary,
    premium: true,
  },
];

export function TiersSection() {
  return (
    <MarketingSection id="tiers">
      <SectionHeader
        align="center"
        description="Three bounded tiers: useful Free access, calmer Pro depth, and VIP preview language without pricing or billing claims."
        eyebrow="Value / tier framing"
        title="Choose your level of support"
      />

      <div className="ppm-tiers-grid">
        {tiers.map((tier) => {
          const pillClasses = tier.premium ? 'ppm-pill--premium' : 'ppm-pill--success';

          return (
            <MarketingCard
              key={tier.name}
              className={tier.featured ? 'ppm-tier-card ppm-tier-card--featured' : 'ppm-tier-card'}
            >
              <div className="ppm-tier-top">
                <h3 className="ppm-tier-title">{tier.name}</h3>
                <StatusPill className={pillClasses}>{tier.label}</StatusPill>
              </div>

              <p className="ppm-tier-positioning">{tier.positioning}</p>
              <p className="ppm-tier-copy">{tier.description}</p>

              <ul>
                {tier.items.map((item) => (
                  <li key={item} className="ppm-tier-list-item">
                    <span className="ppm-check">
                      <Check aria-hidden size={12} />
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>

              {tier.ctaTo.startsWith('#') ? (
                <a className={[tier.ctaClass, 'ppm-tier-cta'].join(' ')} href={tier.ctaTo}>
                  {tier.ctaLabel}
                </a>
              ) : (
                <Link className={[tier.ctaClass, 'ppm-tier-cta'].join(' ')} to={tier.ctaTo}>
                  {tier.ctaLabel}
                </Link>
              )}
            </MarketingCard>
          );
        })}
      </div>

      <p className="ppm-tier-footer">Start with clarity, upgrade when ready.</p>
    </MarketingSection>
  );
}

export default TiersSection;
