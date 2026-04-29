/// <reference types="vitest/globals" />
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import EnterKey from '../EnterKey';
import { AuthProvider } from '../../../lib/auth';
import toast from 'react-hot-toast';

const checkProSessionMock = vi.fn<() => Promise<boolean>>();
const exchangeApiKeyForSessionMock = vi.fn<(apiKey: string) => Promise<boolean>>();
const clearProSessionMock = vi.fn<() => Promise<void>>();
const getStoredApiKeyMock = vi.fn<() => string | null>();
const clearStoredApiKeyMock = vi.fn<() => void>();

vi.mock('../../../api/client', () => ({
  checkProSession: (...args: []) => checkProSessionMock(...args),
  exchangeApiKeyForSession: (apiKey: string) => exchangeApiKeyForSessionMock(apiKey),
  clearProSession: (...args: []) => clearProSessionMock(...args),
}));

vi.mock('../../../auth/storage', () => ({
  getStoredApiKey: (...args: []) => getStoredApiKeyMock(...args),
  setStoredApiKey: vi.fn(),
  clearStoredApiKey: (...args: []) => clearStoredApiKeyMock(...args),
}));


// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock react-router-dom
const mockNavigate = vi.fn();
let mockLocationState: { from?: { pathname: string } } | null = null;
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: any) => children,
  useNavigate: () => mockNavigate,
  useLocation: () => ({ state: mockLocationState }),
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const renderWithProviders = async (component: React.ReactElement) => {
  const rendered = render(
    <AuthProvider>
      {component}
    </AuthProvider>
  );
  await waitFor(() => {
    expect(checkProSessionMock).toHaveBeenCalled();
  });
  return rendered;
};

beforeEach(() => {
  vi.clearAllMocks();
  getStoredApiKeyMock.mockReturnValue(null);
  clearStoredApiKeyMock.mockImplementation(() => {});
  checkProSessionMock.mockResolvedValue(false);
  exchangeApiKeyForSessionMock.mockResolvedValue(true);
  clearProSessionMock.mockResolvedValue(undefined);
  mockLocationState = null;
});

describe('EnterKey', () => {
  it('renders the API key input form', async () => {
    await renderWithProviders(<EnterKey />);

    expect(screen.getByText('onboarding.enterKey.title')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('onboarding.enterKey.placeholder')).toBeInTheDocument();
    expect(screen.getByText('onboarding.enterKey.save')).toBeInTheDocument();
    expect(screen.getByText('onboarding.enterKey.clear')).toBeInTheDocument();
  });

  it('shows error for empty API key', async () => {
    await renderWithProviders(<EnterKey />);

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('onboarding.enterKey.errorEmpty');
    });
  });

  it('shows error for API key shorter than minimum length', async () => {
    await renderWithProviders(<EnterKey />);

    const input = screen.getByPlaceholderText('onboarding.enterKey.placeholder');
    fireEvent.change(input, { target: { value: 'short' } }); // 5 characters, less than minimum

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('auth.apiKey.tooShort');
    });
  });

  it('saves API key when valid', async () => {
    checkProSessionMock.mockResolvedValueOnce(false).mockResolvedValueOnce(true);

    await renderWithProviders(<EnterKey />);

    const input = screen.getByPlaceholderText('onboarding.enterKey.placeholder');
    fireEvent.change(input, { target: { value: 'sk-test12345678901234567890' } });

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('onboarding.enterKey.successSaved');
    });
    expect(exchangeApiKeyForSessionMock).toHaveBeenCalledWith('sk-test12345678901234567890');
  });

  it('returns direct key-entry success to the app home route', async () => {
    checkProSessionMock.mockResolvedValueOnce(false).mockResolvedValueOnce(true);

    await renderWithProviders(<EnterKey />);

    fireEvent.change(screen.getByPlaceholderText('onboarding.enterKey.placeholder'), {
      target: { value: 'sk-test12345678901234567890' },
    });
    fireEvent.click(screen.getByText('onboarding.enterKey.save'));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/app', { replace: true });
    });
  });

  it('preserves protected source route after key-entry success', async () => {
    checkProSessionMock.mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    mockLocationState = { from: { pathname: '/plate' } };

    await renderWithProviders(<EnterKey />);

    fireEvent.change(screen.getByPlaceholderText('onboarding.enterKey.placeholder'), {
      target: { value: 'sk-test12345678901234567890' },
    });
    fireEvent.click(screen.getByText('onboarding.enterKey.save'));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/plate', { replace: true });
    });
  });

  it('clears API key when clear button is clicked', async () => {
    await renderWithProviders(<EnterKey />);

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
    await renderWithProviders(<EnterKey />);

    const clearButton = screen.getByText('onboarding.enterKey.clear');
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(clearProSessionMock).toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
    });
  });
});
