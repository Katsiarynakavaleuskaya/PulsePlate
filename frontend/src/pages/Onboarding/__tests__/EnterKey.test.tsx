/// <reference types="vitest/globals" />
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import EnterKey from '../EnterKey';
import { AuthProvider } from '../../../lib/auth';
import toast from 'react-hot-toast';


// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: any) => children,
  useNavigate: () => mockNavigate,
  useLocation: () => ({ state: null }),
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const renderWithProviders = (component: React.ReactElement) => {
  // Clear any stored API keys before each test
  localStorage.removeItem('pulseplate_api_key');
  sessionStorage.removeItem('pulseplate_api_key');

  return render(
    <AuthProvider>
      {component}
    </AuthProvider>
  );
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('EnterKey', () => {
  it('renders the API key input form', () => {
    renderWithProviders(<EnterKey />);

    expect(screen.getByText('onboarding.enterKey.title')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('onboarding.enterKey.placeholder')).toBeInTheDocument();
    expect(screen.getByText('onboarding.enterKey.save')).toBeInTheDocument();
    expect(screen.getByText('onboarding.enterKey.clear')).toBeInTheDocument();
  });

  it('shows error for empty API key', async () => {
    renderWithProviders(<EnterKey />);

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('onboarding.enterKey.errorEmpty');
    });
  });

  it('shows error for API key shorter than minimum length', async () => {
    renderWithProviders(<EnterKey />);

    const input = screen.getByPlaceholderText('onboarding.enterKey.placeholder');
    fireEvent.change(input, { target: { value: 'short' } }); // 5 characters, less than minimum

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('auth.apiKey.tooShort');
    });
  });

  it('saves API key when valid', async () => {
    renderWithProviders(<EnterKey />);

    const input = screen.getByPlaceholderText('onboarding.enterKey.placeholder');
    fireEvent.change(input, { target: { value: 'sk-test12345678901234567890' } });

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('onboarding.enterKey.successSaved');
    });
  });

  it('clears API key when clear button is clicked', async () => {
    renderWithProviders(<EnterKey />);

    const input = screen.getByPlaceholderText('onboarding.enterKey.placeholder');
    fireEvent.change(input, { target: { value: 'sk-test12345678901234567890' } });

    const clearButton = screen.getByText('onboarding.enterKey.clear');
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('onboarding.enterKey.keyCleared');
      expect(input).toHaveValue('');
    });
  });

  it('does not show success message when clearing empty API key', async () => {
    renderWithProviders(<EnterKey />);

    const clearButton = screen.getByText('onboarding.enterKey.clear');
    fireEvent.click(clearButton);

    // Should not show success message when no key was present
    expect(toast.success).not.toHaveBeenCalled();
  });
});
