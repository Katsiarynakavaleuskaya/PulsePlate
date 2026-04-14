import { Link } from "react-router-dom";
import brandMark from "../../assets/brand/pulseplate-brand-mark.png";
import { MarketingSection } from "./MarketingPrimitives";

const footerGroups = [
    {
        title: "Explore",
        links: [
            { label: "Product preview", href: "#product-preview" },
            { label: "How it works", href: "#how-it-works" },
            { label: "Surfaces", href: "#core-surfaces" },
            { label: "Tiers", href: "#tiers" },
        ],
    },
    {
        title: "Trust",
        links: [
            { label: "Trust & scope", href: "#trust-scope" },
            { label: "See the product", to: "/welcome-gate-v1" },
            { label: "Join early access", to: "/enter-key" },
        ],
    },
];

export function SiteFooter() {
    return (
        <footer>
            <MarketingSection>
                <div className="ppm-footer">
                    <div className="ppm-footer-copy">
                        <div className="ppm-brand">
                            <img
                                alt="PulsePlate brand mark"
                                className="ppm-brand-mark"
                                src={brandMark}
                            />
                            <div className="ppm-brand-copy">
                                <span className="ppm-brand-name">PulsePlate</span>
                                <span className="ppm-brand-tag">Wellness</span>
                            </div>
                        </div>
                        <p className="ppm-description" style={{ fontSize: "0.95rem" }}>
                            A calm, premium wellness control panel built around real product
                            surfaces, honest scope, and bounded guidance.
                        </p>
                        <p className="ppm-footer-note" style={{ marginTop: "0.75rem" }}>
                            Product-first clarity. Quiet confidence.
                        </p>
                    </div>

                    <div className="ppm-footer-links">
                        {footerGroups.map((group) => (
                            <div key={group.title}>
                                <h2 className="ppm-footer-group-title">{group.title}</h2>
                                <div className="ppm-footer-link-list">
                                    {group.links.map((link) =>
                                        "to" in link ? (
                                            <Link
                                                key={link.label}
                                                className="ppm-footer-link"
                                                to={link.to}
                                            >
                                                {link.label}
                                            </Link>
                                        ) : (
                                            <a
                                                key={link.label}
                                                className="ppm-footer-link"
                                                href={link.href}
                                            >
                                                {link.label}
                                            </a>
                                        ),
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </MarketingSection>
        </footer>
    );
}

export default SiteFooter;
