import { Link } from 'react-router-dom';
import { Activity, ArrowRight, Brain, Droplets, Lock, ShieldCheck, Sparkles, Target } from 'lucide-react';
import brandMark from '../../assets/brand/pulseplate-brand-mark.png';
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

const metrics = [
  { label: 'Session status', value: 'Active', accent: 'ppm-dot--green' },
  { label: 'Plan', value: 'Pro', accent: 'ppm-dot--gold' },
  { label: 'AI guidance', value: 'Available', accent: 'ppm-dot--blue' },
  { label: 'Hydration', value: 'Steady', accent: 'ppm-dot--green' },
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
          Wellness-safe product framing
        </a>
      </div>

      <div className="ppm-hero-grid">
        <div className="ppm-hero-copy">
          <p className="ppm-eyebrow">Navy-first calm control panel</p>
          <h1 className="ppm-hero-title">Your calm wellness control panel</h1>
          <p className="ppm-hero-body">
            Understand your metrics, set clear targets, and plan your nutrition with simple
            structure.
          </p>

          <div className="ppm-actions">
            <Link className={marketingButtonClasses.primary} to="/welcome-gate-v1">
              <span>See the product</span>
              <ArrowRight size={16} />
            </Link>
            <Link className={marketingButtonClasses.secondary} to="/enter-key">
              Join early access
            </Link>
          </div>

          <div className="ppm-pill-row">
            <StatusPill className="ppm-pill--success">
              <span className="ppm-dot ppm-dot--green" />
              Available now
            </StatusPill>
            <StatusPill>
              <Lock size={14} />
              Advisory AI
            </StatusPill>
            <StatusPill className="ppm-pill--premium">
              <Sparkles size={14} />
              VIP preview
            </StatusPill>
          </div>
        </div>

        <MarketingCard className="ppm-preview" id="product-preview">
          <div className="ppm-preview-row">
            <StatusPill className="ppm-pill--success">
              <span className="ppm-dot ppm-dot--green" />
              Secure session
            </StatusPill>
            <StatusPill className="ppm-pill--premium">
              <span className="ppm-dot ppm-dot--gold" />
              Pro
            </StatusPill>
          </div>

          <div className="ppm-grid-2">
            {metrics.map((metric) => (
              <div key={metric.label} className="ppm-stat-card">
                <div className="ppm-stat-label">
                  <span className={['ppm-dot', metric.accent].join(' ').trim()} />
                  {metric.label}
                </div>
                <p className="ppm-stat-value">{metric.value}</p>
              </div>
            ))}
          </div>

          <div className="ppm-subsection">
            <div className="ppm-preview-row">
              <p className="ppm-subsection-title">Quick actions</p>
              <p className="ppm-subsection-meta">Available now</p>
            </div>
            <div className="ppm-action-grid">
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
                <p className="ppm-subsection-title">Pro tools</p>
                <Brain size={16} color="var(--pp-blue)" />
              </div>
              <div className="ppm-tool-stack">
                <div className="ppm-tool-item">AI Coach</div>
                <div className="ppm-tool-item">Weekly charts</div>
              </div>
            </div>

            <div className="ppm-insight-card">
              <div className="ppm-preview-row">
                <p className="ppm-subsection-title">AI insight</p>
                <StatusPill className="ppm-pill--neutral">Pro</StatusPill>
              </div>
              <p className="ppm-insight-body">
                Based on your current targets, consider balancing protein intake across meals for
                steadier energy.
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
