import type { JSX } from "react";
import { useEffect } from "react";
import "../../components/marketing/marketing-tokens.css";
import "../../components/marketing/marketing.css";
import {
    CoreSurfacesSection,
    FinalCTASection,
    HeroSection,
    HowItWorksSection,
    ProductStatusBand,
    SiteFooter,
    TiersSection,
    TrustScopeSection,
} from "../../components/marketing";

export default function PulsePlateMarketingPage(): JSX.Element {
    useEffect(() => {
        const previousTitle = document.title;
        document.title = "PulsePlate | Marketing";

        return () => {
            document.title = previousTitle;
        };
    }, []);

    return (
        <main className="ppm-page">
            <HeroSection />
            <ProductStatusBand />
            <HowItWorksSection />
            <CoreSurfacesSection />
            <TiersSection />
            <TrustScopeSection />
            <FinalCTASection />
            <SiteFooter />
        </main>
    );
}
