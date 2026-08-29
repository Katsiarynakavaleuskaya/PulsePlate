import { Link } from 'react-router-dom';
import {
  MarketingCard,
  MarketingSection,
  SectionHeader,
  StatusPill,
  marketingButtonClasses,
} from './MarketingPrimitives';

const informationCards = [
  {
    name: 'Free web tools',
    badge: 'Free',
    body: 'This website is free to use. Purchases are not offered here.',
    ctaLabel: 'Try the free BMI calculator',
    ctaTo: '/bmi',
  },
  {
    name: 'What we’re designing for FitChef',
    badge: 'Apple devices',
    body: 'We’re designing more advanced FitChef features for PulsePlate on Apple devices.',
  },
  {
    name: 'App Store link',
    badge: 'After confirmation',
    body: 'We’ll add a verified App Store link when public availability is confirmed.',
  },
] as const;

export function TiersSection(): JSX.Element {
  return (
    <MarketingSection id="tiers">
      <SectionHeader
        align="center"
        description="Use the free tools on this website and learn more about PulsePlate for Apple devices."
        eyebrow="Free on the web"
        title="Start here for free"
      />

      <div className="ppm-tiers-grid">
        {informationCards.map((card, index) => (
          <MarketingCard
            key={card.name}
            className={index === 0 ? 'ppm-tier-card ppm-tier-card--featured' : 'ppm-tier-card'}
          >
            <div className="ppm-tier-top">
              <h3 className="ppm-tier-title">{card.name}</h3>
              <StatusPill className={index === 0 ? 'ppm-pill--success' : ''}>
                {card.badge}
              </StatusPill>
            </div>
            <p className="ppm-tier-copy">{card.body}</p>
            {'ctaTo' in card ? (
              <Link
                className={[marketingButtonClasses.primary, 'ppm-tier-cta'].join(' ')}
                to={card.ctaTo}
              >
                {card.ctaLabel}
              </Link>
            ) : null}
          </MarketingCard>
        ))}
      </div>

      <p className="ppm-tier-footer">
        For now, this website is free to use and does not offer purchases.
      </p>
    </MarketingSection>
  );
}

export default TiersSection;
