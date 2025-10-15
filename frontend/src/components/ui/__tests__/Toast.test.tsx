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
  Toaster: ({ children, ...props }: any) => (
    <div data-testid="toaster" {...props}>
      {children}
    </div>
  ),
}));

describe('Toaster', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders the toaster component', () => {
    render(<Toaster />);

    expect(screen.getByTestId('toaster')).toBeInTheDocument();
  });

  it('has correct position and styling', () => {
    render(<Toaster />);

    const toaster = screen.getByTestId('toaster');
    expect(toaster).toHaveAttribute('position', 'top-right');
  });
});
