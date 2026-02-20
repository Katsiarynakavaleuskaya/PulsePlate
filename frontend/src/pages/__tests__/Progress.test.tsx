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
    expect(screen.getByRole('link', { name: 'Refresh setup inputs' })).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('radiogroup', { name: 'Progress date range' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '7D' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '30D' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '90D' })).toBeInTheDocument();
    expect(screen.getByTestId('progress-charts')).toBeInTheDocument();
  });

  it('has correct inline styles', () => {
    render(
      <MemoryRouter>
        <Progress />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveStyle({
      backgroundColor: 'var(--pp-navy)',
      minHeight: '100vh'
    });
    expect(main).toHaveClass('p-4');
    expect(main).toHaveClass('pb-24');
  });
});
