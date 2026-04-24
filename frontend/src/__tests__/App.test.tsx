import type { ReactNode } from 'react';
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import App from '../App';

let mockPathname = '/';

const navigateTo = (pathname: string) => {
  mockPathname = pathname;
};

vi.mock('react-router-dom', async () => {
  const React = await import('react');

  return {
    BrowserRouter: ({ children }: { children: ReactNode }) => (
      <>{children}</>
    ),
    useLocation: () => ({ pathname: mockPathname }),
    Routes: ({ children }: { children: ReactNode }) => {
      const routeElements = React.Children.toArray(children) as Array<
        React.ReactElement<{ path?: string; element?: ReactNode }>
      >;
      const matchedRoute = routeElements.find((child) => child.props.path === mockPathname);

      return <>{matchedRoute?.props.element ?? null}</>;
    },
    Route: () => null,
  };
});

// Mock the components that are used in App
vi.mock('../components/TabBar', () => ({
  default: () => <div data-testid="tab-bar">TabBar</div>
}));

vi.mock('../components/ui', () => ({
  Toaster: () => <div data-testid="toaster">Toaster</div>,
  OfflineIndicator: () => <div data-testid="offline-indicator">OfflineIndicator</div>
}));

vi.mock('../auth/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-provider">{children}</div>
  )
}));

vi.mock('../auth/RequireKey', () => ({
  RequireKey: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="require-key">{children}</div>
  )
}));

vi.mock('../lib/settings', () => ({
  SettingsProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="settings-provider">{children}</div>
  )
}));

vi.mock('../config/routes', () => ({
  routes: [
    {
      path: '/',
      component: () => <div data-testid="home-page">Home Page</div>,
      hideTabBar: false,
      requiresAuth: false
    },
    {
      path: '/profile',
      component: () => <div data-testid="profile-page">Profile Page</div>,
      hideTabBar: false,
      requiresAuth: true
    },
    {
      path: '/setup',
      component: () => <div data-testid="setup-page">Setup Page</div>,
      hideTabBar: true,
      requiresAuth: false
    },
    {
      path: '/design-system',
      component: () => <div data-testid="design-system-page">Design System Page</div>,
      hideTabBar: true,
      requiresAuth: false
    },
    {
      path: '/welcome-gate-v1',
      component: () => <div data-testid="welcome-gate-page">Welcome Gate V1 Page</div>,
      hideTabBar: true,
      requiresAuth: false
    },
    {
      path: '/marketing',
      component: () => <div data-testid="marketing-page">Marketing Page</div>,
      hideTabBar: true,
      requiresAuth: false
    }
  ]
}));

describe('App', () => {
  beforeEach(() => {
    navigateTo('/');
  });

  afterEach(() => {
    cleanup();
  });

  it('renders the main app structure', () => {
    render(<App />);

    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
    expect(screen.getByTestId('settings-provider')).toBeInTheDocument();
    expect(screen.getByTestId('toaster')).toBeInTheDocument();
    expect(screen.getByTestId('offline-indicator')).toBeInTheDocument();
  });

  it('renders routes correctly', () => {
    render(<App />);

    // Should render the home page by default
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('shows tab bar when route does not hide it', () => {
    render(<App />);

    expect(screen.getByTestId('tab-bar')).toBeInTheDocument();
  });

  it('hides tab bar for the design system preview route', () => {
    navigateTo('/design-system');

    render(<App />);

    expect(screen.getByTestId('design-system-page')).toBeInTheDocument();
    expect(screen.queryByTestId('tab-bar')).not.toBeInTheDocument();
    expect(screen.queryByTestId('require-key')).not.toBeInTheDocument();
  });

  it('hides tab bar for the welcome gate preview route', () => {
    navigateTo('/welcome-gate-v1');

    render(<App />);

    expect(screen.getByTestId('welcome-gate-page')).toBeInTheDocument();
    expect(screen.queryByTestId('tab-bar')).not.toBeInTheDocument();
    expect(screen.queryByTestId('require-key')).not.toBeInTheDocument();
  });

  it('hides tab bar for the marketing landing route', () => {
    navigateTo('/marketing');

    render(<App />);

    expect(screen.getByTestId('marketing-page')).toBeInTheDocument();
    expect(screen.queryByTestId('tab-bar')).not.toBeInTheDocument();
    expect(screen.queryByTestId('require-key')).not.toBeInTheDocument();
  });
});
