import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { MarketingCard, MarketingSection, marketingButtonClasses } from './MarketingPrimitives';

export function FinalCTASection() {
  return (
    <MarketingSection id="final-cta">
      <MarketingCard className="ppm-cta-card">
        <div className="ppm-cta-grid">
          <div>
            <p className="ppm-eyebrow">Final CTA</p>
            <h2 className="ppm-title ppm-cta-title">
              Ready to explore PulsePlate?
            </h2>
            <p className="ppm-description">
              Start with calm clarity, move through the product at your pace, and unlock more depth
              only when you need it.
            </p>
          </div>

          <div className="ppm-cta-actions">
            <Link className={marketingButtonClasses.primary} to="/welcome-gate-v1">
              <span>See the product</span>
              <ArrowRight size={16} />
            </Link>
            <Link className={marketingButtonClasses.secondary} to="/enter-key">
              Join early access
            </Link>
          </div>
        </div>
      </MarketingCard>
    </MarketingSection>
  );
}

export default FinalCTASection;
