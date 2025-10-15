import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { EmptyState } from '../EmptyState';
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
  });
});
