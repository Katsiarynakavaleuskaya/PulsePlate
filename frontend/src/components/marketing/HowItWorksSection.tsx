import { Activity, ChartLine, Settings2, Sparkles, Utensils } from 'lucide-react';
import { MarketingCard, MarketingSection, SectionHeader } from './MarketingPrimitives';

const steps = [
  {
    title: 'Understand your metrics',
    description:
      'See your current baseline clearly. PulsePlate helps you understand where you are with BMI and wellness-oriented signals.',
    icon: Activity,
  },
  {
    title: 'Complete setup',
    description:
      'Define your core nutrition inputs and preferences. Structured preparation helps PulsePlate guide you more clearly.',
    icon: Settings2,
  },
  {
    title: 'Open Plate',
    description:
      'Access your main daily nutrition surface. Plate is where you plan and structure your meals with calm clarity.',
    icon: Utensils,
  },
  {
    title: 'Review Progress',
    description:
      'Track trends and signals over time. Progress helps you see patterns and stay oriented without over-analysis.',
    icon: ChartLine,
  },
  {
    title: 'Unlock deeper Pro guidance',
    description:
      'Add more depth and structure with Pro. Access AI guidance, weekly insights, and more personalized support where available.',
    icon: Sparkles,
  },
];

export function HowItWorksSection() {
  return (
    <MarketingSection id="how-it-works">
      <SectionHeader
        description="A simple, product-first flow: understand where you are, structure what matters, and unlock more depth only when you need it."
        eyebrow="How it works"
        title="How PulsePlate works"
      />

      <div className="ppm-step-grid">
        {steps.map((step, index) => {
          const Icon = step.icon;

          return (
            <div key={step.title}>
              <MarketingCard className="ppm-step-card">
                <div className="ppm-step-top">
                  <div className="ppm-icon-box">
                    <Icon size={20} />
                  </div>
                  <span className="ppm-step-number">0{index + 1}</span>
                </div>
                <h3 className="ppm-step-title" style={{ marginTop: '1.5rem' }}>
                  {step.title}
                </h3>
                <p className="ppm-step-copy">{step.description}</p>
              </MarketingCard>
            </div>
          );
        })}
      </div>
    </MarketingSection>
  );
}

export default HowItWorksSection;
