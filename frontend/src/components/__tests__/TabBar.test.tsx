// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';

// Mock functions declared before mocks (hoisting-safe)
const mockUseAuth = vi.fn();
const mockUseVipModule = vi.fn();

// Mock the auth context BEFORE imports
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock VIP module hook BEFORE imports
vi.mock('../../lib/useFeatureFlag', () => ({
  useVipModule: () => mockUseVipModule(),
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
    { path: '/vip-feature', label: 'VIP Feature', requiresAuth: true, requiresVip: true },
    { path: '/another-vip', label: 'Another VIP', requiresAuth: true, requiresVip: true },
  ],
}));

// Mock react-router-dom BEFORE imports
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Routes: ({ children }: any) => <>{children}</>,
  Route: ({ element }: any) => element,
  NavLink: ({ to, children, className, ...props }: any) => (
    <a href={to} className={className} {...props}>
      {children}
    </a>
  ),
  useLocation: () => ({ pathname: '/' }),
  matchPath: (config: any, pathname: string) => {
    if (config.path === '/' && pathname === '/') {
      return { path: '/', pathname: '/', params: {}, search: '', hash: '', key: 'default' };
    }
    return null;
  },
}));

import TabBar from '../TabBar';

const renderTabBar = (apiKey: string | null = null) => {
  mockUseAuth.mockReturnValue({ apiKey });

  return render(<TabBar />);
};

describe('TabBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });



  describe('without API key', () => {
    it('shows lock icons for protected routes', () => {
      renderTabBar(null);

      // Check that protected tabs have lock icons
      const plateTab = screen.getByRole('tab', { name: /plate/i });
      const progressTab = screen.getByRole('tab', { name: /progress/i });

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

      const plateTab = screen.getByRole('tab', { name: /plate/i });
      const progressTab = screen.getByRole('tab', { name: /progress/i });

      expect(plateTab).toHaveClass('cursor-not-allowed');
      expect(progressTab).toHaveClass('cursor-not-allowed');

      expect(plateTab).toHaveAttribute('aria-disabled', 'true');
      expect(progressTab).toHaveAttribute('aria-disabled', 'true');
    });

    it('shows click feedback for disabled tabs', async () => {
      renderTabBar(null);

      const plateTab = screen.getByRole('tab', { name: /plate/i });

      // Click on disabled tab
      fireEvent.click(plateTab!);

      // Check for scale animation class
      expect(plateTab).toHaveClass('scale-95');

      // Check for pulse overlay
      const pulseOverlay = plateTab?.querySelector('.bg-primary\\/20');
      expect(pulseOverlay).toBeInTheDocument();

      // Wait for animation to reset after 300ms
      await waitFor(() => {
        expect(plateTab).toHaveClass('scale-100');
        expect(plateTab?.querySelector('.bg-primary\\/20')).not.toBeInTheDocument();
      }, { timeout: 400 });
    });

    it('shows accessible labels for disabled tabs', () => {
      renderTabBar(null);

      const plateTab = screen.getByRole('tab', { name: /plate/i });

      expect(plateTab).toHaveAttribute('title', 'auth.requiresApiKey');
      expect(plateTab).toHaveAttribute('tabindex', '-1');
    });
  });

  describe('with API key', () => {
    it('shows all tabs as accessible', () => {
      renderTabBar('test-api-key');

      // All tabs should be NavLink elements (not disabled spans)
      const homeTab = screen.getByRole('tab', { name: /home/i });
      const plateTab = screen.getByRole('tab', { name: /plate/i });
      const progressTab = screen.getByRole('tab', { name: /progress/i });

      expect(homeTab).toBeInTheDocument();
      expect(plateTab).toBeInTheDocument();
      expect(progressTab).toBeInTheDocument();

      expect(homeTab).toHaveAttribute('href', '/');
      expect(plateTab).toHaveAttribute('href', '/plate');
      expect(progressTab).toHaveAttribute('href', '/progress');
    });

    it('shows active tab indicator bar for the active route', () => {
      renderTabBar('test-api-key');

      // The indicator bar should be present for the "Home" tab (default active route)
      const homeTab = screen.getByRole('tab', { name: /home/i });
      const indicatorBar = homeTab?.querySelector('div.bg-primary.rounded-full');
      expect(indicatorBar).toBeInTheDocument();
    });

    it('shows hover effects for available tabs', () => {
      renderTabBar('test-api-key');

      const homeTab = screen.getByRole('tab', { name: /home/i });

      expect(homeTab).toHaveClass('hover:scale-105');
      expect(homeTab).toHaveClass('transition-all');
    });
  });

  describe('accessibility', () => {
    it('has proper ARIA attributes for disabled tabs', () => {
      renderTabBar(null);

      const plateTab = screen.getByRole('tab', { name: /plate/i });
      const progressTab = screen.getByRole('tab', { name: /progress/i });

      expect(plateTab).toHaveAttribute('aria-disabled', 'true');
      expect(progressTab).toHaveAttribute('aria-disabled', 'true');
      expect(plateTab).toHaveAttribute('tabindex', '-1');
      expect(progressTab).toHaveAttribute('tabindex', '-1');
      expect(plateTab).toHaveAttribute('title', 'auth.requiresApiKey');
      expect(progressTab).toHaveAttribute('title', 'auth.requiresApiKey');
    });
  });

  describe('VIP functionality', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({ apiKey: 'test-key' });
    });

    it('shows VIP tabs when VIP module is enabled', () => {
      mockUseVipModule.mockReturnValue(true);
      renderTabBar('test-key');

      expect(screen.getByRole('tab', { name: /vip feature/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /another vip/i })).toBeInTheDocument();
    });

    it('hides VIP tabs when VIP module is disabled', () => {
      mockUseVipModule.mockReturnValue(false);
      renderTabBar('test-key');

      expect(screen.queryByRole('tab', { name: /vip feature/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /another vip/i })).not.toBeInTheDocument();
    });

    it('shows VIP tabs as disabled when VIP module is disabled but user has API key', () => {
      mockUseVipModule.mockReturnValue(false);
      renderTabBar('test-key');

      // VIP tabs should not be visible at all when VIP is disabled
      expect(screen.queryByRole('tab', { name: /vip feature/i })).not.toBeInTheDocument();
    });

    it('handles more than 6 tabs correctly with grid layout', () => {
      mockUseVipModule.mockReturnValue(true);
      renderTabBar('test-key');

      // Should have 6 tabs total: Home, Profile, Plate, Progress, VIP Feature, Another VIP
      const tabBar = screen.getByRole('tablist');
      expect(tabBar).toHaveClass('grid-cols-6');
    });

    it('shows correct disabled reason for VIP tabs when VIP is disabled', () => {
      mockUseVipModule.mockReturnValue(false);
      renderTabBar('test-key');

      // VIP tabs should not be visible when VIP is disabled
      expect(screen.queryByRole('tab', { name: /vip feature/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /another vip/i })).not.toBeInTheDocument();
    });
  });
});
