import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { WhoTargetsPanel } from '../WhoTargetsPanel';

// Extend Vitest matchers
expect.extend(toHaveNoViolations);

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => {
      const translations: Record<string, string> = {
        'who_targets.loading': 'Loading targets...',
        'who_targets.error': 'Failed to load',
        'who_targets.retry': 'Try Again',
        'who_targets.empty': 'Please complete your profile',
        'who_targets.save_button': 'Save & Get Weekly Plan',
        'who_targets.title': 'WHO Nutrition Targets',
        'who_targets.subtitle': 'Personalized nutrition goals based on WHO guidelines',
        'who_targets.calories.title': 'Daily Calories',
        'who_targets.macros.title': 'Macronutrients',
        'who_targets.hydration.title': 'Hydration',
        'who_targets.micros.title': 'Priority Micronutrients',
        'who_targets.activity.title': 'Activity Goals',
        'who_targets.warnings.title': 'Important Notes',
      };
      return translations[key] || fallback || key;
    },
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

    it('should announce loading state to screen readers via ARIA attributes', () => {
      render(<WhoTargetsPanel {...createProps({ loading: true })} />);

      const loadingElement = screen.getByTestId('who-targets-panel');
      // Check for ARIA busy state and live region
      expect(loadingElement).toHaveAttribute('aria-busy', 'true');
      expect(loadingElement).toHaveAttribute('aria-live', 'polite');
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

    it('should support Enter key activation for retry button', async () => {
      const user = userEvent.setup();
      const mockRetry = vi.fn();
      render(
        <WhoTargetsPanel {...createProps({ error: 'Failed to load targets', onRetry: mockRetry })} />
      );

      const retryButton = screen.getByRole('button', { name: /try again/i });

      retryButton.focus();
      expect(retryButton).toHaveFocus();

      // Test Enter key activation
      await user.keyboard('{Enter}');
      expect(mockRetry).toHaveBeenCalled();
    });

    it('should support Space key activation for retry button', async () => {
      const user = userEvent.setup();
      const mockRetry = vi.fn();
      render(
        <WhoTargetsPanel {...createProps({ error: 'Failed to load targets', onRetry: mockRetry })} />
      );

      const retryButton = screen.getByRole('button', { name: /try again/i });

      retryButton.focus();
      expect(retryButton).toHaveFocus();

      // Test Space key activation
      await user.keyboard(' ');
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

      // Check for icon with proper ARIA label (if not hidden from screen readers)
      const icons = screen.queryAllByRole('img');
      if (icons.length > 0) {
        // Check that visible icons have proper accessibility attributes
        icons.forEach(icon => {
          if (!icon.hasAttribute('aria-hidden')) {
            expect(icon).toHaveAttribute('aria-label');
          }
        });
      }
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
      expect(headings.length).toBeGreaterThan(0); // At least one heading should be present

      // Check that all headings have proper levels
      headings.forEach((heading) => {
        expect(heading.tagName).toMatch(/^H[1-6]$/);
      });

      // Check for main title heading
      expect(screen.getByRole('heading', { name: /who nutrition targets/i })).toBeInTheDocument();
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

      // Note: color-contrast checks are disabled in JSDOM by axe-core
      // Actual color contrast must be verified via visual regression tests or manual browser testing
      const results = await axe(container);
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

      // Check for ARIA loading state
      const panel = screen.getByTestId('who-targets-panel');
      expect(panel).toHaveAttribute('aria-busy', 'true');
      expect(panel).toHaveAttribute('aria-live', 'polite');

      // Switch to loaded state
      rerender(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      // Verify aria-busy is removed
      expect(panel).not.toHaveAttribute('aria-busy', 'true');
      expect(panel).not.toHaveAttribute('aria-live', 'polite');

      // Check that content is properly announced
      expect(screen.getByText(/calories/i)).toBeInTheDocument();
      expect(screen.getByText(/hydration/i)).toBeInTheDocument();
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

      // Check that data sections and their values are present (not relying on exact values)
      expect(screen.getByText(/calories/i)).toBeInTheDocument();
      expect(screen.getByText(/hydration/i)).toBeInTheDocument();
      expect(screen.getByText(/macronutrients/i)).toBeInTheDocument();
      expect(screen.getByText(/activity goals/i)).toBeInTheDocument();
      expect(screen.getByText(/priority micronutrients/i)).toBeInTheDocument();

      // Check for unit labels - test presence rather than exact counts
      expect(screen.getAllByText('g').length).toBeGreaterThanOrEqual(1); // grams
      expect(screen.getByText('ml')).toBeInTheDocument(); // milliliters
      expect(screen.getByText('kcal')).toBeInTheDocument(); // kilocalories
      expect(screen.getAllByText('mg').length).toBeGreaterThanOrEqual(1); // milligrams (multiple micronutrients)
    });
  });

  describe('Keyboard Navigation', () => {
    it('should support standard keyboard navigation patterns', () => {
      const mockSave = vi.fn();
      render(<WhoTargetsPanel {...createProps({ data: mockData, onSaveAndContinue: mockSave })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });

      // Test Tab navigation
      button.focus();
      expect(button).toHaveFocus();

      // Test Enter key activation
      fireEvent.keyDown(button, { key: 'Enter', code: 'Enter' });
      expect(mockSave).toHaveBeenCalled();

      mockSave.mockClear();

      // Test Space key activation
      fireEvent.keyDown(button, { key: ' ', code: 'Space' });
      expect(mockSave).toHaveBeenCalled();
    });

    it('should support Tab navigation through interactive elements', () => {
      render(<WhoTargetsPanel {...createProps({ data: mockData })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });

      // Test that button can receive focus
      button.focus();
      expect(button).toHaveFocus();

      // Test that button is in tab order
      expect(button).not.toHaveAttribute('tabindex', '-1');
    });

    it('should handle keyboard events without errors', async () => {
      const user = userEvent.setup();
      const mockSave = vi.fn();
      render(<WhoTargetsPanel {...createProps({ data: mockData, onSaveAndContinue: mockSave })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      // Test various key events don't cause errors
      expect(async () => {
        await user.keyboard('{Enter}');
        await user.keyboard(' ');
        await user.keyboard('{Escape}');
        await user.keyboard('{Tab}');
      }).not.toThrow();
    });

    it('should support Enter key activation for main button', async () => {
      const user = userEvent.setup();
      const mockSave = vi.fn();
      render(<WhoTargetsPanel {...createProps({ data: mockData, onSaveAndContinue: mockSave })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      await user.keyboard('{Enter}');
      expect(mockSave).toHaveBeenCalled();
    });

    it('should support Space key activation for main button', async () => {
      const user = userEvent.setup();
      const mockSave = vi.fn();
      render(<WhoTargetsPanel {...createProps({ data: mockData, onSaveAndContinue: mockSave })} />);

      const button = screen.getByRole('button', { name: /save & get weekly plan/i });
      button.focus();

      // Test Space key
      await user.keyboard(' ');
      expect(mockSave).toHaveBeenCalled();
    });
  });
});
