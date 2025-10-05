/// <reference types="vitest/globals" />
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
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

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        {component}
      </AuthProvider>
    </BrowserRouter>
  );
};

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
      expect(toast.error).toHaveBeenCalledWith('API key must be at least 20 characters');
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
});
