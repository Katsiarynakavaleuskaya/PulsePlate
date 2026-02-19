import { MemoryRouter } from 'react-router-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import LiveProgressIndicator from '../LiveProgressIndicator';

const mockTrackLiveIndicatorImpression = vi.fn();
const mockTrackCtaImpression = vi.fn();
const mockTrackCtaClick = vi.fn();
const mockTrackPaywallOpen = vi.fn();

vi.mock('../useHppLiveIndicator', () => ({
  useHppLiveIndicator: vi.fn(),
}));

vi.mock('../../../lib/hppTelemetry', () => ({
  trackHppLiveIndicatorImpression: (...args: unknown[]) => mockTrackLiveIndicatorImpression(...args),
  trackHppCtaImpression: (...args: unknown[]) => mockTrackCtaImpression(...args),
  trackHppCtaClick: (...args: unknown[]) => mockTrackCtaClick(...args),
  trackHppPaywallOpenFromLive: (...args: unknown[]) => mockTrackPaywallOpen(...args),
}));

import { useHppLiveIndicator } from '../useHppLiveIndicator';

describe('LiveProgressIndicator', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders static fallback and tracks impressions', () => {
    vi.mocked(useHppLiveIndicator).mockReturnValue({
      status: 'static',
      lastEventAt: null,
      variant: 'compact',
    });

    const { container } = render(
      <MemoryRouter>
        <LiveProgressIndicator source="home" ctaTo="/progress" ctaLabel="Open progress live" />
      </MemoryRouter>
    );

    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByText('Static fallback')).toBeInTheDocument();
    expect(mockTrackLiveIndicatorImpression).toHaveBeenCalledWith({
      source: 'hpp_live_indicator',
      placement: 'home',
      live_status: 'static',
      variant: 'compact',
    });
    expect(mockTrackCtaImpression).toHaveBeenCalledWith({
      source: 'hpp_live_indicator',
      placement: 'home',
      live_status: 'static',
      variant: 'compact',
      cta_to: '/progress',
    });

    expect(screen.getByLabelText('Live progress indicator')).toHaveAttribute('data-variant', 'compact');
    expect(container.firstChild).toMatchSnapshot();
  });

  it('renders live status and tracks click with enriched payload', () => {
    vi.mocked(useHppLiveIndicator).mockReturnValue({
      status: 'live',
      lastEventAt: 1710000000000,
      variant: 'emphasized',
    });

    const { container } = render(
      <MemoryRouter>
        <LiveProgressIndicator source="progress" ctaTo="/setup" ctaLabel="Refresh setup inputs" />
      </MemoryRouter>
    );

    expect(screen.getByText('Live updates on')).toBeInTheDocument();
    expect(screen.getByLabelText('Live event timestamp')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Refresh setup inputs' }));

    expect(mockTrackCtaClick).toHaveBeenCalledWith({
      source: 'hpp_live_indicator',
      placement: 'progress',
      live_status: 'live',
      variant: 'emphasized',
      cta_to: '/setup',
    });
    expect(mockTrackPaywallOpen).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Live progress indicator')).toHaveAttribute('data-variant', 'emphasized');
    expect(container.firstChild).toMatchSnapshot();
  });

  it('tracks paywall open event for paywall-targeted cta', () => {
    vi.mocked(useHppLiveIndicator).mockReturnValue({
      status: 'live',
      lastEventAt: 1710000000000,
      variant: 'compact',
    });

    render(
      <MemoryRouter>
        <LiveProgressIndicator source="plate" ctaTo="/pro" ctaLabel="Open Pro" />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('link', { name: 'Open Pro' }));

    expect(mockTrackPaywallOpen).toHaveBeenCalledWith({
      source: 'hpp_live_indicator',
      placement: 'plate',
      live_status: 'live',
      variant: 'compact',
      cta_to: '/pro',
    });
  });
});
