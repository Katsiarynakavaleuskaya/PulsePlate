import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { Toaster } from '../Toast';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
  Toaster: vi.fn(({ children, ...props }: any) => (
    <div data-testid="toaster" {...props}>
      {children}
    </div>
  )),
}));

describe('Toaster', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders the toaster component', () => {
    render(<Toaster />);

    expect(screen.getByTestId('toaster')).toBeInTheDocument();
  });

  it('configures toaster with correct options', async () => {
    const { Toaster: MockToaster } = await import('react-hot-toast');

    render(<Toaster />);

    expect(MockToaster).toHaveBeenCalledWith(
      expect.objectContaining({
        position: 'top-right',
        toastOptions: expect.objectContaining({
          duration: 4000,
        }),
      }),
      expect.anything()
    );
  });
});
