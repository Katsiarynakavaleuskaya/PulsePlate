import { Link } from 'react-router-dom';
import brandMark from '../../assets/brand/pulseplate-brand-mark.png';
import { MarketingSection } from './MarketingPrimitives';

type FooterLink =
    | { kind: 'anchor'; label: string; href: string }
    | { kind: 'route'; label: string; to: string };

type FooterGroup = {
    title: string;
    links: FooterLink[];
};

const footerGroups: FooterGroup[] = [
    {
        title: 'Explore',
        links: [
            { kind: 'anchor', label: 'FitChef preview', href: '#fitchef-demo' },
            { kind: 'anchor', label: 'How it works', href: '#how-it-works' },
            { kind: 'route', label: 'Free BMI calculator', to: '/bmi' },
            { kind: 'anchor', label: 'Free on the web', href: '#tiers' },
        ],
    },
    {
        title: 'Trust',
        links: [
            { kind: 'anchor', label: 'What this preview does', href: '#trust-scope' },
            { kind: 'anchor', label: 'Back to top', href: '#top' },
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
                        <p className="ppm-description" style={{ fontSize: '0.95rem' }}>
                            Use the free BMI calculator or choose Today or This week in the FitChef
                            preview.
                        </p>
                        <p className="ppm-footer-note" style={{ marginTop: '0.75rem' }}>
                            Everyday wellness planning — not medical advice.
                        </p>
                    </div>

                    <div className="ppm-footer-links">
                        {footerGroups.map((group) => (
                            <div key={group.title}>
                                <h2 className="ppm-footer-group-title">{group.title}</h2>
                                <div className="ppm-footer-link-list">
                                    {group.links.map((link) =>
                                        link.kind === 'route' ? (
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
