import { Compass, MousePointerClick, ShieldCheck } from 'lucide-react';
import { MarketingCard, MarketingSection } from './MarketingPrimitives';

const statusCards = [
  {
    title: 'Use the BMI calculator',
    label: 'Free website',
    description: 'Check BMI with the free tool on this website.',
    icon: ShieldCheck,
    accent: 'var(--pp-green)',
  },
  {
    title: 'Choose Today or This week',
    label: 'FitChef preview',
    description: 'Both choices stay visible until you confirm.',
    icon: MousePointerClick,
    accent: 'var(--pp-blue)',
  },
  {
    title: 'PulsePlate for Apple devices',
    label: 'Apple devices',
    description:
      'Read about the broader FitChef experience planned beyond the free website.',
    icon: Compass,
    accent: 'var(--pp-gold)',
  },
];

export function ProductStatusBand() {
  return (
    <MarketingSection className="ppm-section--tight">
      <div className="ppm-status-grid">
        {statusCards.map(({ title, label, description, icon: Icon, accent }) => (
          <MarketingCard key={title} className="ppm-band-card">
            <div className="ppm-band-top">
              <div className="ppm-icon-box" style={{ color: accent }}>
                <Icon size={20} />
              </div>
              <div>
                <p className="ppm-supporting">{label}</p>
                <h3 className="ppm-band-card-title" style={{ marginTop: '0.5rem' }}>
                  {title}
                </h3>
              </div>
            </div>
            <p className="ppm-band-card-copy">{description}</p>
          </MarketingCard>
        ))}
      </div>
    </MarketingSection>
  );
}

export default ProductStatusBand;
