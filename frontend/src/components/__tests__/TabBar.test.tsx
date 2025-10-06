// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TabBar from '../TabBar';
import { AuthProvider } from '../../auth/AuthContext';

// Mock the auth context
const mockUseAuth = vi.fn();
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock routes config
vi.mock('../../config/routes', () => ({
  tabRoutes: [
    { path: '/', label: 'Home', requiresAuth: false },
    { path: '/profile', label: 'Profile', requiresAuth: false },
    { path: '/plate', label: 'Plate', requiresAuth: true },
    { path: '/progress', label: 'Progress', requiresAuth: true },
  ],
}));

const renderTabBar = (apiKey: string | null = null) => {
  mockUseAuth.mockReturnValue({ apiKey });

  return render(
    <BrowserRouter>
      <AuthProvider>
        <TabBar />
      </AuthProvider>
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

    it('shows click feedback for disabled tabs', () => {
      renderTabBar(null);

      const plateTab = screen.getByText('Plate').closest('div');

      // Click on disabled tab
      fireEvent.click(plateTab!);

      // Check for scale animation class
      expect(plateTab).toHaveClass('scale-95');
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
    });

    it('has proper ARIA attributes for enabled tabs', () => {
      renderTabBar('test-api-key');

      const homeTab = screen.getByText('Home').closest('a');

      expect(homeTab).toHaveAttribute('role', 'tab');
      expect(homeTab).toHaveAttribute('aria-selected');
    });
  });
});
