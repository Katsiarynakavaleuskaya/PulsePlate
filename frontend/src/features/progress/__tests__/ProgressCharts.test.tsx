/** @vitest-environment jsdom */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
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
  afterEach(() => {
    cleanup();
  });

  it('renders progress tracking header', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Progress Tracking')).toBeInTheDocument();
    expect(screen.getByText('Monitor your health journey (MONTH)')).toBeInTheDocument();
  });

  it('renders export PDF button', () => {
    render(<ProgressCharts />);

    const exportButton = screen.getByText('Export PDF');
    expect(exportButton).toBeInTheDocument();
    expect(screen.getByTestId('download-icon')).toBeInTheDocument();
  });

  it('renders weight and BMI progress chart', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Weight & BMI Progress')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('renders calorie balance chart', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Calorie Balance')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders macronutrient distribution chart', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Macronutrient Distribution')).toBeInTheDocument();
    expect(screen.getByText('Nutrient Breakdown')).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('displays weight change indicator', () => {
    render(<ProgressCharts />);

    // The mock data shows weight loss (72.8 - 73.2 = -0.4), so should show trending down
    expect(screen.getByTestId('trending-down-icon')).toBeInTheDocument();
    expect(screen.getByText('0.4 kg lost')).toBeInTheDocument();
  });

  it('displays macronutrient breakdown', () => {
    render(<ProgressCharts />);

    expect(screen.getByText('Protein')).toBeInTheDocument();
    expect(screen.getByText('Carbs')).toBeInTheDocument();
    expect(screen.getByText('Fat')).toBeInTheDocument();
    expect(screen.getByText('Fiber')).toBeInTheDocument();
    expect(screen.getByText('Other')).toBeInTheDocument();
  });
});
