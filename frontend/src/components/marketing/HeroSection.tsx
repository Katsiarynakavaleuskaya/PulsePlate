import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  CalendarDays,
  Compass,
  Lock,
  ShieldCheck,
  Sparkles,
  UtensilsCrossed,
} from 'lucide-react';
import brandMark from '../../assets/brand/pulseplate-brand-mark.png';
import fitChefHero from '../../assets/brand/fitchef-portrait-neutral-v1.png';
import {
  MarketingCard,
  MarketingSection,
  StatusPill,
  marketingButtonClasses,
} from './MarketingPrimitives';

const quickActions = [
  { label: 'Daily Plate', icon: UtensilsCrossed, helper: 'For today' },
  { label: 'Free BMI calculator', icon: Activity, helper: 'On this website' },
  { label: 'FitChef choice', icon: Compass, helper: 'Today or this week' },
  { label: 'Weekly Planning', icon: CalendarDays, helper: 'For seven days' },
];

const launchSignals = [
  { label: 'Website', value: 'Free BMI calculator', accent: 'ppm-dot--green' },
  { label: 'FitChef', value: 'Today or this week', accent: 'ppm-dot--blue' },
  { label: 'Today', value: 'Daily Plate', accent: 'ppm-dot--gold' },
  { label: 'This week', value: 'Weekly Planning', accent: 'ppm-dot--green' },
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
          <p className="ppm-eyebrow">Free on the web</p>
          <h1 className="ppm-hero-title">Check your BMI and see how FitChef works</h1>
          <p className="ppm-hero-body">
            Use the free BMI calculator, or choose Today or This week in the FitChef preview to see
            whether it points to Daily Plate or Weekly Planning.
          </p>

          <div className="ppm-actions">
            <a className={marketingButtonClasses.primary} href="#fitchef-demo">
              <span>See how FitChef works</span>
              <ArrowRight size={16} />
            </a>
            <Link className={marketingButtonClasses.secondary} to="/bmi">
              Try the free BMI calculator
            </Link>
          </div>

          <div className="ppm-pill-row">
            <StatusPill className="ppm-pill--success">
              <span className="ppm-dot ppm-dot--green" />
              Free website
            </StatusPill>
            <StatusPill>
              <Lock size={14} />
              No purchases here
            </StatusPill>
            <StatusPill className="ppm-pill--premium">
              <Sparkles size={14} />
              Prepared FitChef preview
            </StatusPill>
          </div>
        </div>

        <MarketingCard aria-label="PulsePlate product preview" className="ppm-preview" id="product-preview">
          <div className="ppm-fitchef-hero">
            <img alt="FitChef wellness guide" className="ppm-fitchef-image" src={fitChefHero} />
            <div>
              <p className="ppm-fitchef-kicker">FitChef</p>
              <p className="ppm-fitchef-copy">
                A short preview of how FitChef connects a choice to a planning view.
              </p>
            </div>
          </div>

          <div className="ppm-preview-row">
            <StatusPill className="ppm-pill--success">
              <span className="ppm-dot ppm-dot--green" />
              Prepared example
            </StatusPill>
            <StatusPill className="ppm-pill--premium">
              <span className="ppm-dot ppm-dot--gold" />
              Nothing is saved
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
              <p className="ppm-subsection-title">Try the two choices</p>
              <p className="ppm-subsection-meta">Today or this week</p>
            </div>
            <div className="ppm-action-grid" aria-hidden="true">
              {quickActions.map(({ label, icon: Icon, helper }) => (
                <div key={label} className="ppm-action-card">
                  <div className="ppm-action-icon">
                    <Icon size={16} />
                  </div>
                  <span className="ppm-action-copy">
                    <span className="ppm-action-text">{label}</span>
                    <span className="ppm-action-helper">{helper}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="ppm-preview-lower">
            <div className="ppm-panel">
              <div className="ppm-preview-row">
                <p className="ppm-subsection-title">Planning views</p>
                <ShieldCheck size={16} color="var(--pp-blue)" />
              </div>
              <div className="ppm-tool-stack">
                <div className="ppm-tool-item">Today’s plate</div>
                <div className="ppm-tool-item">This week</div>
              </div>
            </div>

            <div className="ppm-insight-card">
              <div className="ppm-preview-row">
                <p className="ppm-subsection-title">FitChef result</p>
                <StatusPill className="ppm-pill--neutral">Prepared example</StatusPill>
              </div>
              <p className="ppm-insight-body">
                Today points to Daily Plate. This week points to Weekly Planning.
              </p>
              <div className="ppm-insight-note">
                <Lock size={14} color="var(--pp-green)" />
                This preview uses no personal data.
              </div>
            </div>
          </div>
        </MarketingCard>
      </div>
    </MarketingSection>
  );
}

export default HeroSection;
