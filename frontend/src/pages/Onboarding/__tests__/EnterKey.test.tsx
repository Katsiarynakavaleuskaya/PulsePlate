import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import EnterKey from '../EnterKey';
import { AuthProvider } from '../../../lib/auth';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
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
    // Mock alert
    const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {});

    renderWithProviders(<EnterKey />);

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith('onboarding.enterKey.errorEmpty');
    });

    alertMock.mockRestore();
  });

  it('saves API key when valid', async () => {
    const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {});

    renderWithProviders(<EnterKey />);

    const input = screen.getByPlaceholderText('onboarding.enterKey.placeholder');
    fireEvent.change(input, { target: { value: 'sk-test123456789' } });

    const saveButton = screen.getByText('onboarding.enterKey.save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith('onboarding.enterKey.successSaved');
    });

    alertMock.mockRestore();
  });
});
