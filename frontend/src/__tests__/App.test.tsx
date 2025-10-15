import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

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
    }
  ]
}));

describe('App', () => {
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
});
