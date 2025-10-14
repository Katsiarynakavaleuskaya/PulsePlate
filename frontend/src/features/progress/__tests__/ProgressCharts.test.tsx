/** @vitest-environment jsdom */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProgressCharts from '../ProgressCharts';

// Mock recharts components
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ children }: any) => <div data-testid="pie">{children}</div>,
  Cell: () => <div data-testid="cell" />,
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Download: () => <div data-testid="download-icon" />,
  TrendingUp: () => <div data-testid="trending-up-icon" />,
  TrendingDown: () => <div data-testid="trending-down-icon" />,
}));

describe('ProgressCharts', () => {
  it('renders progress tracking header', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Progress Tracking')).toBeInTheDocument();
    expect(screen.getByText('Monitor your health journey')).toBeInTheDocument();
  });

  it('renders export PDF button', () => {
    render(<ProgressCharts />);

    const exportButton = screen.getAllByText('Export PDF')[0];
    expect(exportButton).toBeInTheDocument();
    expect(screen.getAllByTestId('download-icon')[0]).toBeInTheDocument();
  });

  it('renders weight and BMI progress chart', () => {
    render(<ProgressCharts />);

    expect(screen.getAllByText('Weight & BMI Progress')[0]).toBeInTheDocument();
    expect(screen.getAllByTestId('line-chart')[0]).toBeInTheDocument();
  });

  it('renders calorie balance chart', () => {
    render(<ProgressCharts />);

    expect(screen.getAllByText('Calorie Balance')[0]).toBeInTheDocument();
    expect(screen.getAllByTestId('bar-chart')[0]).toBeInTheDocument();
  });

  it('renders macronutrient distribution chart', () => {
    render(<ProgressCharts />);

    expect(screen.getAllByText('Macronutrient Distribution')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Nutrient Breakdown')[0]).toBeInTheDocument();
    expect(screen.getAllByTestId('pie-chart')[0]).toBeInTheDocument();
  });

  it('displays weight change indicator', () => {
    render(<ProgressCharts />);

    // The mock data shows weight loss (72.8 - 73.2 = -0.4), so should show trending down
    expect(screen.getAllByTestId('trending-down-icon')[0]).toBeInTheDocument();
    expect(screen.getAllByText('0.4 kg lost')[0]).toBeInTheDocument();
  });

  it('displays macronutrient breakdown', () => {
    render(<ProgressCharts />);

    expect(screen.getAllByText('Protein')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Carbs')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Fat')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Fiber')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Other')[0]).toBeInTheDocument();
  });
});
