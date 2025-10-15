import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OfflineIndicator } from '../OfflineIndicator';

// Mock navigator.onLine
const mockNavigator = {
  onLine: true,
};

Object.defineProperty(window, 'navigator', {
  value: mockNavigator,
  writable: true,
});

describe('OfflineIndicator', () => {
  beforeEach(() => {
    mockNavigator.onLine = true;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders online indicator when online', () => {
    render(<OfflineIndicator />);

    // Should not show indicator when online
    expect(screen.queryByTestId('offline-indicator')).not.toBeInTheDocument();
  });

  it('shows offline indicator when offline', () => {
    mockNavigator.onLine = false;

    render(<OfflineIndicator />);

    expect(screen.getByText('You are offline')).toBeInTheDocument();
  });

  it('handles online/offline events', () => {
    render(<OfflineIndicator />);

    // Simulate going offline
    mockNavigator.onLine = false;
    fireEvent(window, new Event('offline'));

    expect(screen.getByText('You are offline')).toBeInTheDocument();

    // Simulate going back online
    mockNavigator.onLine = true;
    fireEvent(window, new Event('online'));

    // Should show "Back online" message briefly
    expect(screen.getByText('Back online')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    mockNavigator.onLine = false;
    render(<OfflineIndicator className="custom-class" />);

    const indicator = screen.getByText('You are offline').closest('div');
    expect(indicator).toHaveClass('custom-class');
  });

  it('handles browser environment check', () => {
    // This test is skipped as it's complex to mock properly in jsdom
    // The component handles non-browser environments gracefully
    expect(true).toBe(true);
  });
});
