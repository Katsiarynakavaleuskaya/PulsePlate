import { Compass, Eye, Shield, Sparkles } from 'lucide-react';
import { MarketingCard, MarketingSection, SectionHeader, StatusPill } from './MarketingPrimitives';

const trustItems = [
  {
    title: 'For everyday planning, not medical advice',
    description:
      'PulsePlate supports everyday wellness planning. It does not diagnose, treat, or replace professional care.',
    icon: Shield,
  },
  {
    title: 'The prepared preview uses no personal data',
    description:
      'Your choice stays in this card. The example does not save it, open another area, or change a plan.',
    icon: Eye,
  },
  {
    title: 'The website does not run FitChef AI',
    description:
      'The result is prepared in advance to show the simple choice-to-product-area correspondence.',
    icon: Compass,
  },
];

const faqItems = [
  {
    question: 'What can I use on this website?',
    answer:
      'You can use the free BMI calculator and try the prepared FitChef preview without a purchase step.',
  },
  {
    question: 'Does the FitChef preview run AI?',
    answer:
      'No. It uses one fixed result for each of the two choices.',
  },
  {
    question: 'Where are more advanced FitChef ideas planned?',
    answer:
      'PulsePlate is being designed for Apple devices. This page does not claim current App Store availability.',
  },
];

export function TrustScopeSection() {
  return (
    <MarketingSection id="trust-scope">
      <SectionHeader
        description="Learn what the free website offers, how the FitChef preview works, and what is planned for Apple devices."
        eyebrow="Clear boundaries"
        title="Know what to expect"
      />

      <div className="ppm-trust-layout" style={{ marginTop: '2.5rem' }}>
        <div className="ppm-trust-grid">
          {trustItems.map(({ title, description, icon: Icon }) => (
            <MarketingCard key={title} className="ppm-trust-card">
              <div className="ppm-trust-top">
                <div className="ppm-icon-box">
                  <Icon size={20} />
                </div>
                <h3 className="ppm-trust-title">{title}</h3>
              </div>
              <p className="ppm-trust-copy">{description}</p>
            </MarketingCard>
          ))}
        </div>

        <MarketingCard className="ppm-trust-card">
          <div className="ppm-faq-top" style={{ justifyContent: 'space-between' }}>
            <div>
              <p className="ppm-eyebrow">Questions you may have</p>
              <h3 className="ppm-tier-title" style={{ marginTop: '0.5rem' }}>
                A quick, honest guide
              </h3>
            </div>
            <StatusPill>
              <Sparkles size={14} />
              Clear boundaries
            </StatusPill>
          </div>

          <div style={{ display: 'grid', gap: '1rem', marginTop: '1.5rem' }}>
            {faqItems.map((item) => (
              <div key={item.question} className="ppm-faq-item">
                <h4 className="ppm-faq-title">{item.question}</h4>
                <p className="ppm-faq-copy">{item.answer}</p>
              </div>
            ))}
          </div>
        </MarketingCard>
      </div>
    </MarketingSection>
  );
}

export default TrustScopeSection;
