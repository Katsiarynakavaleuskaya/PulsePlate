import { Link } from 'react-router-dom';
import { Activity, ArrowRight, Brain, Droplets, Lock, ShieldCheck, Sparkles, Target } from 'lucide-react';
import brandMark from '../../assets/brand/pulseplate-brand-mark.png';
import fitChefHero from '../../assets/brand/fitchef-onboarding-welcome-v1.png';
import {
  MarketingCard,
  MarketingSection,
  StatusPill,
  marketingButtonClasses,
} from './MarketingPrimitives';

const quickActions = [
  { label: 'Open Plate', icon: Target },
  { label: 'Check BMI', icon: Activity },
  { label: 'Complete Setup', icon: ShieldCheck },
  { label: 'View Progress', icon: Sparkles },
];

const launchSignals = [
  { label: 'Meals', value: 'Plan today', accent: 'ppm-dot--green' },
  { label: 'Progress', value: 'Track gently', accent: 'ppm-dot--gold' },
  { label: 'FitChef', value: 'Guided tips', accent: 'ppm-dot--blue' },
  { label: 'Boundaries', value: 'Wellness only', accent: 'ppm-dot--green' },
];

export function HeroSection() {
  return (
    <MarketingSection className="ppm-hero" id="top">
      <div className="ppm-hero-topline">
        <div className="ppm-brand">
          <img alt="PulsePlate brand mark" className="ppm-brand-mark" src={brandMark} />
          <div className="ppm-brand-copy">
            <span className="ppm-brand-name">PulsePlate</span>
            <span className="ppm-brand-tag">Wellness</span>
          </div>
        </div>
        <a className="ppm-hero-link" href="#trust-scope">
          Wellness-safe guidance
        </a>
      </div>

      <div className="ppm-hero-grid">
        <div className="ppm-hero-copy">
          <p className="ppm-eyebrow">AI wellness coach trio</p>
          <h1 className="ppm-hero-title">Plan meals, habits, and progress in one calm place</h1>
          <p className="ppm-hero-body">
            PulsePlate pairs simple nutrition structure with FitChef guidance, progress tracking,
            and gentle habit support for everyday wellness decisions.
          </p>

          <div className="ppm-actions">
            <Link className={marketingButtonClasses.primary} to="/app">
              <span>Open the app</span>
              <ArrowRight size={16} />
            </Link>
            <Link className={marketingButtonClasses.secondary} to="/enter-key">
              Join early access
            </Link>
          </div>

          <div className="ppm-pill-row">
            <StatusPill className="ppm-pill--success">
              <span className="ppm-dot ppm-dot--green" />
              Wellness planner
            </StatusPill>
            <StatusPill>
              <Lock size={14} />
              Privacy-minded
            </StatusPill>
            <StatusPill className="ppm-pill--premium">
              <Sparkles size={14} />
              FitChef preview
            </StatusPill>
          </div>
        </div>

        <MarketingCard className="ppm-preview" id="product-preview">
          <div className="ppm-fitchef-hero">
            <img alt="FitChef wellness guide" className="ppm-fitchef-image" src={fitChefHero} />
            <div>
              <p className="ppm-fitchef-kicker">FitChef</p>
              <p className="ppm-fitchef-copy">Friendly meal and habit guidance without medical claims.</p>
            </div>
          </div>

          <div className="ppm-preview-row">
            <StatusPill className="ppm-pill--success">
              <span className="ppm-dot ppm-dot--green" />
              Launch preview
            </StatusPill>
            <StatusPill className="ppm-pill--premium">
              <span className="ppm-dot ppm-dot--gold" />
              Early access
            </StatusPill>
          </div>

          <div className="ppm-grid-2">
            {launchSignals.map((signal) => (
              <div key={signal.label} className="ppm-stat-card">
                <div className="ppm-stat-label">
                  <span className={['ppm-dot', signal.accent].join(' ').trim()} />
                  {signal.label}
                </div>
                <p className="ppm-stat-value">{signal.value}</p>
              </div>
            ))}
          </div>

          <div className="ppm-subsection">
            <div className="ppm-preview-row">
              <p className="ppm-subsection-title">Quick actions</p>
              <p className="ppm-subsection-meta">Available now</p>
            </div>
            <div className="ppm-action-grid" aria-hidden="true">
              {quickActions.map(({ label, icon: Icon }) => (
                <div key={label} className="ppm-action-card">
                  <div className="ppm-action-icon">
                    <Icon size={16} />
                  </div>
                  <span className="ppm-action-text">{label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="ppm-preview-lower">
            <div className="ppm-panel">
              <div className="ppm-preview-row">
                <p className="ppm-subsection-title">Coach lanes</p>
                <Brain size={16} color="var(--pp-blue)" />
              </div>
              <div className="ppm-tool-stack">
                <div className="ppm-tool-item">Nutrition structure</div>
                <div className="ppm-tool-item">Habit check-ins</div>
              </div>
            </div>

            <div className="ppm-insight-card">
              <div className="ppm-preview-row">
                <p className="ppm-subsection-title">FitChef note</p>
                <StatusPill className="ppm-pill--neutral">Advisory</StatusPill>
              </div>
              <p className="ppm-insight-body">
                Try pairing a simple protein target with one repeatable meal habit for the week.
              </p>
              <div className="ppm-insight-note">
                <Droplets size={14} color="var(--pp-green)" />
                Guidance with clear boundaries
              </div>
            </div>
          </div>
        </MarketingCard>
      </div>
    </MarketingSection>
  );
}

export default HeroSection;
