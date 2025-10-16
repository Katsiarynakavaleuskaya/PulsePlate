import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { Toaster, showSuccess, showError, showInfo, showWarning, showLoading, dismissToast, dismissAllToasts } from '../Toast';
import { Info, AlertCircle } from 'lucide-react';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => {
  const mockToast = vi.fn() as any;
  mockToast.success = vi.fn();
  mockToast.error = vi.fn();
  mockToast.loading = vi.fn();
  mockToast.dismiss = vi.fn();

  return {
    default: mockToast,
    Toaster: vi.fn(({ children, ...props }: any) => (
      <div data-testid="toaster" {...props}>
        {children}
      </div>
    )),
  };
});

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

describe('Toast functions', () => {
  let mockToast: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    const toastModule = await import('react-hot-toast');
    mockToast = toastModule.default;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('showSuccess calls toast.success with message', () => {
    const message = 'Success message';
    showSuccess(message);
    expect(mockToast.success).toHaveBeenCalledWith(message);
  });

  it('showError calls toast.error with message', () => {
    const message = 'Error message';
    showError(message);
    expect(mockToast.error).toHaveBeenCalledWith(message);
  });

  it('showInfo calls toast with message and info icon', () => {
    const message = 'Info message';
    showInfo(message);
    expect(mockToast).toHaveBeenCalledWith(message, {
      icon: expect.objectContaining({
        type: Info,
      }),
    });
  });

  it('showWarning calls toast with message and warning icon', () => {
    const message = 'Warning message';
    showWarning(message);
    expect(mockToast).toHaveBeenCalledWith(message, {
      icon: expect.objectContaining({
        type: AlertCircle,
      }),
      style: {
        borderColor: 'rgba(245, 158, 11, 0.3)',
      },
    });
  });

  it('showLoading calls toast.loading with message and returns toast id', () => {
    const message = 'Loading message';
    const mockToastId = 'toast-123';
    mockToast.loading.mockReturnValue(mockToastId);

    const result = showLoading(message);
    expect(mockToast.loading).toHaveBeenCalledWith(message);
    expect(result).toBe(mockToastId);
  });

  it('dismissToast calls toast.dismiss with toast id', () => {
    const toastId = 'toast-123';
    dismissToast(toastId);
    expect(mockToast.dismiss).toHaveBeenCalledWith(toastId);
  });

  it('dismissAllToasts calls toast.dismiss without arguments', () => {
    dismissAllToasts();
    expect(mockToast.dismiss).toHaveBeenCalledWith();
  });
});
