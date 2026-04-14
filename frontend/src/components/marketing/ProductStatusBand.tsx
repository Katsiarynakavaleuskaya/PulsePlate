import { Lock, ShieldCheck, Sparkles } from 'lucide-react';
import { MarketingCard, MarketingSection } from './MarketingPrimitives';

const statusCards = [
  {
    title: 'A real product, not a concept site',
    label: 'Live now',
    description:
      'PulsePlate wraps existing Home, Setup, Plate, Progress, BMI, and Pro surfaces into one calm control flow.',
    icon: ShieldCheck,
    accent: 'var(--pp-green)',
  },
  {
    title: 'Guidance with clear boundaries',
    label: 'Wellness-safe',
    description:
      'AI remains an advisory layer inside the product. It does not replace the product experience or turn into medical framing.',
    icon: Lock,
    accent: 'var(--pp-blue)',
  },
  {
    title: 'VIP remains explicitly bounded',
    label: 'Preview scope',
    description:
      'More personalized support and automation stay clearly labeled as preview or where available, without invented claims.',
    icon: Sparkles,
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
