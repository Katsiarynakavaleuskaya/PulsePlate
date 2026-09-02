import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import fitChefHeroStretch from '../../assets/brand/fitchef-hero-stretch-v1.webp';
import brandMark from '../../assets/brand/pulseplate-brand-mark.png';
import { MarketingSection, marketingButtonClasses } from './MarketingPrimitives';

const heroImagePriority = { fetchpriority: 'high' } as const;

export function HeroSection() {
  return (
    <MarketingSection className="ppm-hero" id="top">
      <div className="ppm-hero-topline">
        <div className="ppm-brand">
          <img alt="PulsePlate brand mark" className="ppm-brand-mark" src={brandMark} />
          <div className="ppm-brand-copy">
            <span className="ppm-brand-name">PulsePlate</span>
          </div>
        </div>
      </div>

      <div className="ppm-hero-grid">
        <div className="ppm-hero-copy">
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
        </div>

        <figure className="ppm-hero-scenario" id="product-preview">
          <div className="ppm-hero-scenario-media">
            <img
              alt="FitChef, a tabby cat stretching on an exercise mat"
              className="ppm-hero-scenario-image"
              data-fitchef-hero-asset="fitchef-hero-stretch-v1.webp"
              decoding="async"
              height={1402}
              loading="eager"
              src={fitChefHeroStretch}
              width={1122}
              {...heroImagePriority}
            />
          </div>
        </figure>
      </div>
    </MarketingSection>
  );
}

export default HeroSection;
