import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { EmptyState, NoChartsAvailable, NoProgressData } from '../EmptyState';
import { TrendingUp, BarChart3 } from 'lucide-react';

describe('EmptyState', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders with default FileX icon', () => {
    render(
      <EmptyState
        title="No data"
        description="There is no data to display"
      />
    );

    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByText('There is no data to display')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('data-state', 'empty');
  });

  it('renders with custom icon', () => {
    render(
      <EmptyState
        icon={TrendingUp}
        title="No trends"
        description="No trending data available"
      />
    );

    expect(screen.getByText('No trends')).toBeInTheDocument();
    expect(screen.getByText('No trending data available')).toBeInTheDocument();
  });

  it('renders with action button', () => {
    render(
      <EmptyState
        icon={BarChart3}
        title="No charts"
        description="No chart data available"
        action={<button>Create Chart</button>}
      />
    );

    expect(screen.getByText('No charts')).toBeInTheDocument();
    expect(screen.getByText('No chart data available')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create Chart' })).toBeInTheDocument();
  });

  it('uses alert semantics without duplicate live-region attributes when requested', () => {
    render(
      <EmptyState
        state="error"
        title="Failed"
        description="Unable to load"
      />
    );

    expect(screen.getByRole('alert')).not.toHaveAttribute('aria-live');
  });

  it('uses polite status semantics for loading state', () => {
    render(
      <EmptyState
        state="loading"
        title="Loading"
        description="Please wait"
      />
    );

    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('data-state', 'loading');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });

  it('has correct CSS classes', () => {
    render(
      <EmptyState
        title="Test"
        description="Test description"
      />
    );

    const container = screen.getByText('Test').closest('div');
    expect(container).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'min-h-[300px]', 'p-8', 'text-center');
  });

  it('renders icon with correct styling', () => {
    render(
      <EmptyState
        icon={TrendingUp}
        title="Test"
        description="Test description"
      />
    );

    const iconContainer = screen.getByText('Test').closest('div')?.querySelector('div');
    expect(iconContainer).toHaveClass('rounded-full', 'bg-gray-100', 'dark:bg-gray-800', 'p-4', 'mb-4');
    expect(iconContainer).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders built-in start action through governed Button', () => {
    const handleStartTracking = vi.fn();
    render(<NoProgressData onStartTracking={handleStartTracking} />);

    const action = screen.getByRole('button', { name: 'Start Tracking' });
    expect(action).toHaveClass('bg-[var(--color-primary)]', 'min-h-[44px]');
    fireEvent.click(action);
    expect(handleStartTracking).toHaveBeenCalledTimes(1);
  });

  it('does not render a no-op start action without a handler', () => {
    render(<NoProgressData />);

    expect(screen.queryByRole('button', { name: 'Start Tracking' })).not.toBeInTheDocument();
  });

  it('renders built-in retry action through governed secondary Button', () => {
    const handleRetry = vi.fn();
    render(<NoChartsAvailable onRetry={handleRetry} />);

    const action = screen.getByRole('button', { name: 'Retry' });
    expect(action).toHaveClass('border', 'border-[var(--color-border)]');
    fireEvent.click(action);
    expect(handleRetry).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('alert')).toHaveAttribute('data-state', 'error');
  });
});
