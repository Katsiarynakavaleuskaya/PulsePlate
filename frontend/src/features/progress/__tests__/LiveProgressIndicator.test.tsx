import { MemoryRouter } from 'react-router-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import LiveProgressIndicator from '../LiveProgressIndicator';

const mockTrackLiveIndicatorImpression = vi.fn();
const mockTrackCtaImpression = vi.fn();
const mockTrackCtaClick = vi.fn();

vi.mock('../useHppLiveIndicator', () => ({
  useHppLiveIndicator: vi.fn(),
}));

vi.mock('../../../lib/hppTelemetry', () => ({
  trackHppLiveIndicatorImpression: (...args: unknown[]) => mockTrackLiveIndicatorImpression(...args),
  trackHppCtaImpression: (...args: unknown[]) => mockTrackCtaImpression(...args),
  trackHppCtaClick: (...args: unknown[]) => mockTrackCtaClick(...args),
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
    });

    render(
      <MemoryRouter>
        <LiveProgressIndicator source="home" ctaTo="/progress" ctaLabel="Open progress live" />
      </MemoryRouter>
    );

    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByText('Static fallback')).toBeInTheDocument();
    expect(mockTrackLiveIndicatorImpression).toHaveBeenCalledWith({
      source: 'home',
      live_status: 'static',
    });
    expect(mockTrackCtaImpression).toHaveBeenCalledWith({
      source: 'home',
      live_status: 'static',
      cta_to: '/progress',
    });
  });

  it('renders live status and tracks click', () => {
    vi.mocked(useHppLiveIndicator).mockReturnValue({
      status: 'live',
      lastEventAt: 1710000000000,
    });

    render(
      <MemoryRouter>
        <LiveProgressIndicator source="progress" ctaTo="/setup" ctaLabel="Refresh setup inputs" />
      </MemoryRouter>
    );

    expect(screen.getByText('Live updates on')).toBeInTheDocument();
    expect(screen.getByLabelText('Live event timestamp')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Refresh setup inputs' }));

    expect(mockTrackCtaClick).toHaveBeenCalledWith({
      source: 'progress',
      live_status: 'live',
      cta_to: '/setup',
    });
  });
});
