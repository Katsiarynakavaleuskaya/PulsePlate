import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { MarketingCard, MarketingSection, marketingButtonClasses } from './MarketingPrimitives';

export function FinalCTASection() {
  return (
    <MarketingSection id="final-cta">
      <MarketingCard className="ppm-cta-card">
        <div className="ppm-cta-grid">
          <div>
            <h2 className="ppm-title ppm-cta-title">
              Try the BMI calculator or FitChef preview
            </h2>
            <p className="ppm-description">Both are free to use on this website.</p>
          </div>

          <div className="ppm-cta-actions">
            <Link className={marketingButtonClasses.primary} to="/bmi">
              <span>Try free BMI</span>
              <ArrowRight size={16} />
            </Link>
            <a className={marketingButtonClasses.secondary} href="#fitchef-demo">
              Return to the FitChef preview
            </a>
          </div>
        </div>
      </MarketingCard>
    </MarketingSection>
  );
}

export default FinalCTASection;
