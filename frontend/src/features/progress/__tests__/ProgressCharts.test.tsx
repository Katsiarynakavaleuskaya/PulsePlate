/** @vitest-environment jsdom */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';

import ProgressCharts from '../ProgressCharts';

vi.mock('lucide-react', () => ({
  Download: () => <div data-testid="download-icon" />,
  BarChart3: () => <div data-testid="bar-chart-icon" />,
}));

describe('ProgressCharts', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders progress tracking header', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Progress Tracking')).toBeInTheDocument();
    expect(screen.getByText('Monitor your health journey (MONTH)')).toBeInTheDocument();
  });

  it('disables export until live progress data exists', () => {
    render(<ProgressCharts />);

    const exportButton = screen.getByRole('button', { name: /export .*pdf/i });
    expect(exportButton).toBeInTheDocument();
    expect(exportButton).toBeDisabled();
  });

  it('shows a trusted empty state instead of fabricated charts', () => {
    render(<ProgressCharts />);

    expect(screen.getByTestId('bar-chart-icon')).toBeInTheDocument();
    expect(screen.getByText('No progress data yet')).toBeInTheDocument();
    expect(
      screen.getByText(/PulsePlate hides charts for month views until real nutrition and weight data/i)
    ).toBeInTheDocument();
  });
});
