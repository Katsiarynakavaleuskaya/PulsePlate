import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Progress from '../Progress';

// Mock ProgressCharts component
vi.mock('../../features/progress/ProgressCharts', () => ({
  default: () => <div data-testid="progress-charts">ProgressCharts</div>
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe('Progress', () => {
  it('renders progress page with ProgressCharts', () => {
    render(
      <MemoryRouter>
        <Progress />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Progress' })).toBeInTheDocument();
    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Update setup parameters' })).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('button', { name: 'WEEK' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'MONTH' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'QUARTER' })).toBeInTheDocument();
    expect(screen.getByTestId('progress-charts')).toBeInTheDocument();
  });

  it('has expected layout classes', () => {
    render(
      <MemoryRouter>
        <Progress />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('flex');
    expect(main).toHaveClass('min-h-screen');
    expect(main).toHaveClass('flex-col');
    expect(main).toHaveClass('bg-[var(--color-bg)]');
  });
});
