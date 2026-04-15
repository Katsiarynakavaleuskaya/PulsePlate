import { Brain, Eye, Shield, Sparkles } from 'lucide-react';
import { MarketingCard, MarketingSection, SectionHeader, StatusPill } from './MarketingPrimitives';

const trustItems = [
  {
    title: 'Wellness-focused, not medical advice',
    description:
      'PulsePlate supports interpretation and planning in a wellness context. It does not position itself as diagnosis, treatment, or clinician workflow.',
    icon: Shield,
  },
  {
    title: 'Privacy-conscious by design',
    description:
      'Secure session state, bounded product surfaces, and calm product framing keep the experience grounded in trust instead of noisy growth claims.',
    icon: Eye,
  },
  {
    title: 'AI stays inside clear product boundaries',
    description:
      'AI guidance is advisory and gated. The product remains the hero, with structured Home, Setup, Plate, Progress, BMI, and Pro surfaces.',
    icon: Brain,
  },
];

const faqItems = [
  {
    question: 'What is available now?',
    answer:
      'Home, Setup, Plate, Progress, BMI, Pro, secure session state, premium indicators, compact status cards, quick actions, and gated AI insight.',
  },
  {
    question: 'What is still marked as preview?',
    answer:
      'Expanded Pro tools, richer progress views, saved insight history, refined onboarding presentation, FAQ and launch updates, and deeper VIP personalization where available.',
  },
  {
    question: 'What will not appear on this site?',
    answer:
      'Invented features like barcode scanning, restaurant ordering, meal delivery, social feed, wearable sync, clinician portal, fake testimonials, or fake checkout flows.',
  },
];

export function TrustScopeSection() {
  return (
    <MarketingSection id="trust-scope">
      <SectionHeader
        description="Trust comes from constraints: honest availability labels, privacy-conscious framing, and zero invented product claims."
        eyebrow="Trust / scope"
        title="Built with care and clarity"
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
              <p className="ppm-eyebrow">Honest availability</p>
              <h3 className="ppm-tier-title" style={{ marginTop: '0.5rem' }}>
                FAQ and scope snapshot
              </h3>
            </div>
            <StatusPill>
              <Sparkles size={14} />
              Preview aware
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
