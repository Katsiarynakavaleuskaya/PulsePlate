/** @vitest-environment jsdom */
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';

const {
  mockToastError,
  mockHtml2Canvas,
  mockPdfSave,
  mockPdfAddImage,
  mockPdfAddPage,
  mockJsPdf,
} = vi.hoisted(() => {
  const hoistedMockToastError = vi.fn();
  const hoistedMockHtml2Canvas = vi.fn();
  const hoistedMockPdfSave = vi.fn();
  const hoistedMockPdfAddImage = vi.fn();
  const hoistedMockPdfAddPage = vi.fn();
  const hoistedMockJsPdf = vi.fn(() => ({
    addImage: hoistedMockPdfAddImage,
    addPage: hoistedMockPdfAddPage,
    save: hoistedMockPdfSave,
  }));

  return {
    mockToastError: hoistedMockToastError,
    mockHtml2Canvas: hoistedMockHtml2Canvas,
    mockPdfSave: hoistedMockPdfSave,
    mockPdfAddImage: hoistedMockPdfAddImage,
    mockPdfAddPage: hoistedMockPdfAddPage,
    mockJsPdf: hoistedMockJsPdf,
  };
});

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: mockToastError,
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('../../components/ui', async () => {
  const actual = await vi.importActual<typeof import('../../components/ui')>('../../components/ui');
  return {
    ...actual,
  };
});

vi.mock('html2canvas', () => ({
  default: mockHtml2Canvas,
}));

vi.mock('jspdf', () => ({
  jsPDF: mockJsPdf,
}));

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
  beforeEach(() => {
    mockToastError.mockReset();
    mockHtml2Canvas.mockReset();
    mockPdfSave.mockReset();
    mockPdfAddImage.mockReset();
    mockPdfAddPage.mockReset();
    mockJsPdf.mockClear();
    document.body.innerHTML = '';
  });

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

    const exportButton = screen.getByRole('button', { name: 'Export progress report as PDF' });
    expect(exportButton).toBeInTheDocument();
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

  it('exports the progress report as PDF on success', async () => {
    mockHtml2Canvas.mockResolvedValue({
      width: 1000,
      height: 1400,
      toDataURL: () => 'data:image/png;base64,fake-image',
    });

    render(<ProgressCharts />);

    fireEvent.click(screen.getByRole('button', { name: 'Export progress report as PDF' }));

    await waitFor(() => {
      expect(mockHtml2Canvas).toHaveBeenCalledTimes(1);
      expect(mockJsPdf).toHaveBeenCalledWith('p', 'mm', 'a4');
      expect(mockPdfSave).toHaveBeenCalledWith('progress-report.pdf');
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it('shows an error toast when export fails', async () => {
    mockHtml2Canvas.mockRejectedValue(new Error('canvas unavailable'));

    render(<ProgressCharts />);

    fireEvent.click(screen.getByRole('button', { name: 'Export progress report as PDF' }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith('Failed to export PDF: canvas unavailable');
    });
  });
});
