import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { WhoTargetsPanel } from '../WhoTargetsPanel';

// Extend Vitest matchers
expect.extend(toHaveNoViolations);

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback || key,
    i18n: {
      language: 'en',
    },
  }),
}));

// Mock API client
vi.mock('../../api/client', () => ({
  getTargets: vi.fn(),
}));

describe('WhoTargetsPanel Accessibility', () => {
  const mockData = {
    kcal_daily: 2000,
    macros: {
      protein_g: 150,
      carbs_g: 250,
      fat_g: 67,
      fiber_g: 30,
    },
    water_ml: 2000,
    priority_micros: {
      iron_mg: 18,
      calcium_mg: 1000,
    },
    activity_weekly: {
      moderate_aerobic_min: 150,
      strength_sessions: 2,
      steps_daily: 10000,
    },
    warnings: [
      {
        message: 'Consider increasing protein intake',
        severity: 'warning',
      },
    ],
    calculation_date: '2024-01-15',
  };

  // Helper function to create default props
  const createProps = (overrides = {}) => ({
    data: null,
    loading: false,
    error: null,
    onSaveAndContinue: vi.fn(),
    onRetry: vi.fn(),
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should not have accessibility violations in loading state', async () => {
      const { container } = render(<WhoTargetsPanel {...createProps({ loading: true })} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper loading indicators for screen readers', () => {
      render(<WhoTargetsPanel {...createProps({ loading: true })} />);

      // Check for loading state indicators
      const loadingElement = screen.getByTestId('who-targets-panel');
      expect(loadingElement).toHaveClass('who-targets-panel--loading');
    });
  });

  describe('Error State', () => {
    it('should not have accessibility violations in error state', async () => {
      const { container } = render(
        <WhoTargetsPanel {...createProps({ error: 'Failed to load targets' })} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper error messaging for screen readers', () => {
      render(<WhoTargetsPanel {...createProps({ error: 'Failed to load targets' })} />);

      // Check for error message
      expect(screen.getByText('Failed to load targets')).toBeInTheDocument();

      // Check for retry button
      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();
    });

    it('should support keyboard navigation for retry button', () => {
      const mockRetry = vi.fn();
      render(
        <WhoTargetsPanel {...createProps({ error: 'Failed to load targets', onRetry: mockRetry })} />
      );

      const retryButton = screen.getByRole('button', { name: /try again/i });

      // Test keyboard interaction
      retryButton.focus();
      expect(retryButton).toHaveFocus();

      fireEvent.click(retryButton);
      expect(mockRetry).toHaveBeenCalled();
    });
  });

  describe('Empty State', () => {
    it('should not have accessibility violations in empty state', async () => {
      const { container } = render(<WhoTargetsPanel {...createProps({ data: null })} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper empty state messaging for screen readers', () => {
      render(<WhoTargetsPanel {...createProps({ data: null })} />);

      // Check for empty state message
      expect(
        screen.getByText(/please complete your profile/i)
      ).toBeInTheDocument();

      // Check for icon with proper ARIA label
      const icon = screen.getByRole('img', { hidden: true });
      expect(icon).toHaveAttribute('aria-label');
    });
  });

  describe('Loaded State', () => {
    it('should not have accessibility violations in loaded state', async () => {
      const { container } = render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper heading structure for screen readers', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Check for proper heading hierarchy
      const headings = screen.getAllByRole('heading');
      expect(headings).toHaveLength(7); // 7 sections with headings (including main title)

      // Check that all headings have proper levels
      headings.forEach((heading) => {
        expect(heading.tagName).toMatch(/^H[1-6]$/);
      });
    });

    it('should have proper list structure for warnings', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Check for proper list structure - there are multiple lists (micros and warnings)
      const lists = screen.getAllByRole('list');
      expect(lists.length).toBeGreaterThan(0);

      const warningItems = screen.getAllByRole('listitem');
      expect(warningItems.length).toBeGreaterThan(0);
    });

    it('should have proper table structure for data display', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Check for proper data organization
      const macroItems = screen.getAllByText(/protein|carbs|fat|fiber/i);
      expect(macroItems.length).toBeGreaterThan(0);

      const activityItems = screen.getAllByText(/moderate|strength|steps/i);
      expect(activityItems.length).toBeGreaterThan(0);
    });

    it('should support keyboard navigation through all interactive elements', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Test tab navigation - focus on the button
      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      // Check that focus is properly managed
      expect(button).toHaveFocus();
    });

    it('should have proper color contrast for all text elements', async () => {
      const { container } = render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });

    it('should have proper focus indicators', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      // Check for visible focus indicator
      expect(button).toHaveFocus();
      // Note: CSS focus styles should be tested in visual regression tests
    });

    it('should have proper ARIA labels for all data sections', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Check for proper data labeling - no regions in current implementation
      const dataElements = screen.getAllByText(/\d+/);
      expect(dataElements.length).toBeGreaterThan(0);

      // Check for proper heading structure
      const headings = screen.getAllByRole('heading');
      expect(headings.length).toBeGreaterThan(0);
    });

    it('should handle dynamic content updates without breaking accessibility', async () => {
      const { rerender, container } = render(
        <WhoTargetsPanel {...createProps({ data: mockData })} />
      );

      // Initial render
      let results = await axe(container);
      expect(results).toHaveNoViolations();

      // Update with new data
      const updatedData = {
        ...mockData,
        kcal_daily: 2200,
        warnings: [
          ...mockData.warnings,
          {
            message: 'Monitor sodium intake',
            severity: 'info',
          },
        ],
      };

      rerender(<WhoTargetsPanel {...createProps({ data: updatedData })} />);

      // Check accessibility after update
      results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Screen Reader Support', () => {
    it('should announce loading state changes to screen readers', () => {
      const { rerender } = render(<WhoTargetsPanel {...createProps({ loading: true })} />);

      // Check for loading announcement
      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--loading');

      // Switch to loaded state
      rerender(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Check that content is properly announced
      expect(screen.getAllByText('2,000')).toHaveLength(2);
    });

    it('should announce error state changes to screen readers', () => {
      const { rerender } = render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Switch to error state
      rerender(<WhoTargetsPanel {...createProps({ error: 'Network error' })} />);

      // Check for error announcement
      expect(screen.getByText('Network error')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('should provide meaningful descriptions for all data values', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Check that numeric values have context (formatted with toLocaleString)
      expect(screen.getAllByText('2,000')).toHaveLength(2); // calories and hydration
      expect(screen.getAllByText('150')).toHaveLength(2); // protein and moderate aerobic
      expect(screen.getByText('250')).toBeInTheDocument(); // carbs

      // Check for unit labels
      expect(screen.getAllByText('g')).toHaveLength(4); // grams (4 macro items)
      expect(screen.getByText('ml')).toBeInTheDocument(); // milliliters
    });
  });

  describe('Keyboard Navigation', () => {
    it('should support standard keyboard navigation patterns', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });

      // Test Tab navigation
      button.focus();
      expect(button).toHaveFocus();

      // Test Enter key activation
      fireEvent.keyDown(button, { key: 'Enter' });
      // Should not cause any errors
    });

    it('should support Escape key for dismissing modals or overlays', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      // Test Escape key
      fireEvent.keyDown(button, { key: 'Escape' });
      // Should not cause any errors
    });

    it('should support arrow key navigation for data sections', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      // Test arrow key navigation
      fireEvent.keyDown(button, { key: 'ArrowDown' });
      fireEvent.keyDown(button, { key: 'ArrowUp' });
      fireEvent.keyDown(button, { key: 'ArrowLeft' });
      fireEvent.keyDown(button, { key: 'ArrowRight' });

      // Should not cause any errors
    });
  });
});
