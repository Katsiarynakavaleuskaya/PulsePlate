import type { JSX } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Activity, CalendarDays, Compass, MousePointerClick } from 'lucide-react';
import { MarketingCard, MarketingSection, SectionHeader } from './MarketingPrimitives';

type HowItWorksStep = {
  id: string;
  title: string;
  description: string;
  icon: LucideIcon;
};

const steps: HowItWorksStep[] = [
  {
    id: 'free-bmi',
    title: 'Open the free BMI calculator',
    description: 'View your BMI result on the website.',
    icon: Activity,
  },
  {
    id: 'choose-start',
    title: 'Choose Today or This week',
    description: 'Both choices stay visible in the FitChef preview.',
    icon: MousePointerClick,
  },
  {
    id: 'see-pointer',
    title: 'See the result',
    description: 'The confirmed result stays in the preview card.',
    icon: CalendarDays,
  },
  {
    id: 'apple-direction',
    title: 'Read about PulsePlate for Apple devices',
    description: 'Learn where the more advanced FitChef experience is planned.',
    icon: Compass,
  },
];

export function HowItWorksSection(): JSX.Element {
  return (
    <MarketingSection id="how-it-works">
      <SectionHeader
        description="Check BMI, choose Today or This week, and see the result in the same card."
        eyebrow="How it works"
        title="Use the calculator, then try FitChef"
      />

      <div className="ppm-step-grid">
        {steps.map((step, index) => {
          const Icon = step.icon;

          return (
            <div key={step.id}>
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
