// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock the auth context BEFORE imports
const mockUseAuth = vi.fn();
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock react-i18next BEFORE imports
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock routes config BEFORE imports
vi.mock('../../config/routes', () => ({
  tabRoutes: [
    { path: '/', label: 'Home', requiresAuth: false },
    { path: '/profile', label: 'Profile', requiresAuth: false },
    { path: '/plate', label: 'Plate', requiresAuth: true },
    { path: '/progress', label: 'Progress', requiresAuth: true },
  ],
}));

import TabBar from '../TabBar';

const renderTabBar = (apiKey: string | null = null) => {
  mockUseAuth.mockReturnValue({ apiKey });

  return render(
    <BrowserRouter>
      <TabBar />
    </BrowserRouter>
  );
};

describe('TabBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('without API key', () => {
    it('shows lock icons for protected routes', () => {
      renderTabBar(null);

      // Check that protected tabs have lock icons
      const plateTab = screen.getByText('Plate').closest('div');
      const progressTab = screen.getByText('Progress').closest('div');

      expect(plateTab).toBeInTheDocument();
      expect(progressTab).toBeInTheDocument();

      // Check for lock SVG icons - they should be present in the overlay div
      const plateLockIcon = plateTab?.querySelector('svg');
      const progressLockIcon = progressTab?.querySelector('svg');

      expect(plateLockIcon).toBeInTheDocument();
      expect(progressLockIcon).toBeInTheDocument();

      // Check SVG paths contain lock icon path
      expect(plateLockIcon).toHaveAttribute('viewBox', '0 0 24 24');
      expect(progressLockIcon).toHaveAttribute('viewBox', '0 0 24 24');
    });

    it('shows disabled styling for protected routes', () => {
      renderTabBar(null);

      const plateTab = screen.getByText('Plate').closest('div');
      const progressTab = screen.getByText('Progress').closest('div');

      expect(plateTab).toHaveClass('cursor-not-allowed');
      expect(progressTab).toHaveClass('cursor-not-allowed');

      expect(plateTab).toHaveAttribute('aria-disabled', 'true');
      expect(progressTab).toHaveAttribute('aria-disabled', 'true');
    });

    it('shows click feedback for disabled tabs', async () => {
      renderTabBar(null);

      const plateTab = screen.getByText('Plate').closest('div');

      // Click on disabled tab
      fireEvent.click(plateTab!);

      // Check for scale animation class
      expect(plateTab).toHaveClass('scale-95');

      // Check for pulse overlay
      const pulseOverlay = plateTab?.querySelector('.bg-red-500\\/20');
      expect(pulseOverlay).toBeInTheDocument();

      // Wait for animation to reset after 300ms
      await waitFor(() => {
        expect(plateTab).toHaveClass('scale-100');
        expect(plateTab?.querySelector('.bg-red-500\\/20')).not.toBeInTheDocument();
      }, { timeout: 400 });
    });

    it('shows accessible labels for disabled tabs', () => {
      renderTabBar(null);

      const plateTab = screen.getByText('Plate').closest('div');

      expect(plateTab).toHaveAttribute('title', 'auth.requiresApiKey');
      expect(plateTab).toHaveAttribute('tabindex', '-1');
    });
  });

  describe('with API key', () => {
    it('shows all tabs as accessible', () => {
      renderTabBar('test-api-key');

      // All tabs should be NavLink elements (not disabled spans)
      const homeTab = screen.getByText('Home').closest('a');
      const plateTab = screen.getByText('Plate').closest('a');
      const progressTab = screen.getByText('Progress').closest('a');

      expect(homeTab).toBeInTheDocument();
      expect(plateTab).toBeInTheDocument();
      expect(progressTab).toBeInTheDocument();

      expect(homeTab).toHaveAttribute('href', '/');
      expect(plateTab).toHaveAttribute('href', '/plate');
      expect(progressTab).toHaveAttribute('href', '/progress');
    });

    it('shows hover effects for available tabs', () => {
      renderTabBar('test-api-key');

      const homeTab = screen.getByText('Home').closest('a');

      expect(homeTab).toHaveClass('hover:scale-105');
      expect(homeTab).toHaveClass('transition-all');
    });
  });

  describe('accessibility', () => {
    it('has proper ARIA attributes for disabled tabs', () => {
      renderTabBar(null);

      const plateTab = screen.getByText('Plate').closest('div');
      const progressTab = screen.getByText('Progress').closest('div');

      expect(plateTab).toHaveAttribute('aria-disabled', 'true');
      expect(progressTab).toHaveAttribute('aria-disabled', 'true');
      expect(plateTab).toHaveAttribute('tabindex', '-1');
      expect(progressTab).toHaveAttribute('tabindex', '-1');
      expect(plateTab).toHaveAttribute('title', 'auth.requiresApiKey');
      expect(progressTab).toHaveAttribute('title', 'auth.requiresApiKey');
    });
  });
});
