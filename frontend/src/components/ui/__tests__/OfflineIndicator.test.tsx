import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react';
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
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders online indicator when online', () => {
    render(<OfflineIndicator />);

    // Should not show indicator when online
    expect(screen.queryByText('You are offline')).not.toBeInTheDocument();
    expect(screen.queryByText('Back online')).not.toBeInTheDocument();
  });

  it('shows offline indicator when offline', () => {
    mockNavigator.onLine = false;

    render(<OfflineIndicator />);

    expect(screen.getByText('You are offline')).toBeInTheDocument();
  });

  it('handles online/offline events', () => {
    vi.useFakeTimers();
    render(<OfflineIndicator />);

    // Simulate going offline
    mockNavigator.onLine = false;
    act(() => {
      fireEvent(window, new Event('offline'));
    });

    expect(screen.getByText('You are offline')).toBeInTheDocument();

    // Simulate going back online
    mockNavigator.onLine = true;
    act(() => {
      fireEvent(window, new Event('online'));
    });

    // Should show "Back online" message briefly
    expect(screen.getByText('Back online')).toBeInTheDocument();

    // Verify message disappears after 3 seconds
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.queryByText('Back online')).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it('applies custom className', () => {
    mockNavigator.onLine = false;
    render(<OfflineIndicator className="custom-class" />);

    const indicator = screen.getByRole('status');
    expect(indicator).toHaveClass('custom-class');
  });

});
