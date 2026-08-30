import { Activity, CalendarDays, ChartColumnBig, Compass, UtensilsCrossed } from 'lucide-react';
import { MarketingCard, MarketingSection, SectionHeader, StatusPill } from './MarketingPrimitives';

const surfaces = [
  {
    title: 'Free BMI calculator',
    description: 'Use the calculator on this website.',
    supporting: 'Free web tool',
    icon: Activity,
  },
  {
    title: 'FitChef preview',
    description: 'Choose Today or This week, then confirm.',
    supporting: 'Prepared example',
    icon: Compass,
  },
  {
    title: 'Daily Plate',
    description: 'A day-focused area for planning meals.',
    supporting: 'Today',
    icon: UtensilsCrossed,
  },
  {
    title: 'Weekly Planning',
    description: 'A seven-day area for looking ahead.',
    supporting: 'This week',
    icon: CalendarDays,
  },
  {
    title: 'PulsePlate for Apple devices',
    description:
      'A broader daily and weekly experience is being designed beyond this free website.',
    supporting: 'Apple devices',
    icon: ChartColumnBig,
  },
];

export function CoreSurfacesSection() {
  return (
    <MarketingSection id="core-surfaces">
      <SectionHeader
        description="These are the two planning areas named by the FitChef preview."
        eyebrow="Explore PulsePlate"
        title="Daily Plate and Weekly Planning"
      />

      <div className="ppm-surfaces-grid" style={{ marginTop: '2.5rem' }}>
        {surfaces.map(({ title, description, supporting, icon: Icon }) => (
          <MarketingCard key={title} className="ppm-surface-card">
            <div className="ppm-surface-top">
              <div className="ppm-icon-box">
                <Icon size={20} />
              </div>
              <StatusPill>{supporting}</StatusPill>
            </div>
            <h3 className="ppm-surface-title" style={{ marginTop: '1.5rem' }}>
              {title}
            </h3>
            <p className="ppm-surface-copy">{description}</p>
          </MarketingCard>
        ))}
      </div>
    </MarketingSection>
  );
}

export default CoreSurfacesSection;
