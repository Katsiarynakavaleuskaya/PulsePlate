import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { vi, expect, describe, it, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { Toggle } from '../ui/Toggle';
import { FormField, FormError } from '../ui/FormField';

// Helper function to safely check accessibility violations
const expectNoViolations = (results: any) => {
  try {
    // Prefer matcher when available
    // @ts-ignore - matcher may not be typed in this context
    expect(results).toHaveNoViolations();
  } catch {
    // Fallback when matcher is not registered
    expect(results.violations.length).toBe(0);
  }
};

describe('Accessibility Tests', () => {
  afterEach(() => {
    cleanup();
  });

  describe('Toggle Component', () => {
    it('label click toggles state and respects disabled', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      const { rerender } = render(
        <div>
          <Toggle label="Label Toggle" checked={false} onChange={onChange} />
        </div>
      );
      await user.click(screen.getByText('Label Toggle'));
      expect(onChange).toHaveBeenCalledWith(true);

      onChange.mockClear();
      rerender(
        <div>
          <Toggle label="Label Toggle" checked={false} onChange={onChange} disabled />
        </div>
      );
      await user.click(screen.getByText('Label Toggle'));
      expect(onChange).not.toHaveBeenCalled();
    });

    it('label click transfers focus to switch element', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <div>
          <Toggle label="Focus Transfer Toggle" checked={false} onChange={onChange} />
        </div>
      );

      const switchElement = screen.getByRole('switch');
      const label = screen.getByText('Focus Transfer Toggle');

      // Click the label
      await user.click(label);

      // Verify that focus is transferred to the switch element
      expect(switchElement).toHaveFocus();
      expect(onChange).toHaveBeenCalledWith(true);
    });

    it('should not have accessibility violations when checked', async () => {
      const { container } = render(
        <Toggle
          label="Test Toggle"
          checked={true}
          onChange={() => {}}
        />
      );
      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should not have accessibility violations when unchecked', async () => {
      const { container } = render(
        <Toggle
          label="Test Toggle"
          checked={false}
          onChange={() => {}}
        />
      );
      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should properly associate label with switch using aria-labelledby', async () => {
      const { container } = render(
        <div>
          <Toggle
            label="Accessibility Test Toggle"
            checked={true}
            onChange={() => {}}
          />
        </div>
      );
      const switchElement = screen.getByRole('switch');
      const labelId = switchElement.getAttribute('aria-labelledby')!;

      // Verify that aria-labelledby is set and points to a valid element
      expect(labelId).toMatch(/^toggle-label-/);

      // Find the label element by its ID
      const label = document.getElementById(labelId)!;
      expect(label.textContent).toBe('Accessibility Test Toggle');
      expect(switchElement).toHaveAccessibleName('Accessibility Test Toggle');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should not have accessibility violations when disabled', async () => {
      const { container } = render(
        <div>
          <Toggle
            label="Disabled Toggle"
            checked={false}
            onChange={() => {}}
            disabled={true}
          />
        </div>
      );

      const switchElement = screen.getByRole('switch');
      expect(switchElement).toBeDisabled();
      expect(switchElement).toHaveClass('cursor-not-allowed');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('exposes only the switch in tab order', async () => {
      const user = userEvent.setup();
      const { container } = render(
        <div>
          <Toggle label="Tab Order" checked={false} onChange={() => {}} />
        </div>
      );
      const input = container.querySelector('input[type="checkbox"]');
      const sw = screen.getByRole('switch');
      await user.tab();
      expect(sw).toHaveFocus();
      // The visually hidden input should not be focusable via Tab
      expect(document.activeElement).not.toBe(input);
    });

    it('should support keyboard navigation and interaction', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      const { container } = render(
        <div>
          <Toggle
            label="Keyboard Test Toggle"
            checked={false}
            onChange={handleChange}
          />
        </div>
      );

      const switchElement = screen.getByRole('switch');

      // Focus the element directly
      switchElement.focus();
      expect(switchElement).toHaveFocus();

      // Test click interaction
      await user.click(switchElement);
      expect(handleChange).toHaveBeenCalledWith(true);

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should have proper focus management and visible focus styles', async () => {
      const { container } = render(
        <div>
          <Toggle
            label="Focus Test Toggle"
            checked={false}
            onChange={() => {}}
          />
        </div>
      );

      const switchElement = screen.getByRole('switch');

      // Verify element can receive focus
      switchElement.focus();
      expect(switchElement).toHaveFocus();

      // Verify focus styles are applied (focus:ring-2 focus:ring-blue-600)
      expect(switchElement).toHaveClass('focus:ring-2', 'focus:ring-blue-600', 'focus:ring-offset-2');

      const results = await axe(container);
      expectNoViolations(results);
    });


    it('should have proper ARIA attributes and state management', async () => {
      const { container, rerender } = render(
        <div>
          <Toggle
            label="ARIA Test Toggle"
            checked={false}
            onChange={() => {}}
          />
        </div>
      );

      const switchElement = screen.getByRole('switch');

      // Test initial state
      expect(switchElement).toHaveAttribute('aria-checked', 'false');
      expect(switchElement).not.toHaveAttribute('aria-disabled');

      // Test checked state
      rerender(
        <div>
          <Toggle
            label="ARIA Test Toggle"
            checked={true}
            onChange={() => {}}
          />
        </div>
      );
      expect(switchElement).toHaveAttribute('aria-checked', 'true');
      const updatedSwitch = screen.getByRole('switch');
      expect(updatedSwitch).toHaveAttribute('aria-checked', 'true');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it.skip('should pass color contrast accessibility checks', async () => {
      // JSDOM does not compute real styles, so axe color-contrast rule reports false negatives.
      // Covered by browser-based axe run in Playwright suite (frontend/tests/accessibility.spec.ts).
      const { container } = render(
        <div>
          <Toggle
            label="Contrast Test Toggle"
            checked={true}
            onChange={() => {}}
          />
        </div>
      );

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true }
        }
      });
      expectNoViolations(results);
    });
  });

  describe('FormField Component', () => {
    it('should not have accessibility violations with basic input', async () => {
      const { container } = render(
        <div>
          <FormField
            label="Test Field"
            name="test"
            placeholder="Enter text"
          />
        </div>
      );

      const input = screen.getByLabelText('Test Field');
      expect(input).toHaveAttribute('id', 'test');
      expect(input).toHaveAttribute('name', 'test');
      expect(input).toHaveAttribute('placeholder', 'Enter text');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should properly handle required fields and ARIA attributes', async () => {
      const { container } = render(
        <div>
          <FormField
            label="Required Field"
            name="required"
            required={true}
          />
        </div>
      );

      const input = screen.getByLabelText(/Required Field/);
      expect(input).toHaveAttribute('aria-required', 'true');

      const label = screen.getByText('Required Field');
      expect(label).toHaveTextContent('*');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should properly associate error messages with inputs', async () => {
      const error = { message: 'This field is required', type: 'required' };

      const { container } = render(
        <div>
          <FormField
            label="Error Field"
            name="error"
            error={error}
          />
        </div>
      );

      const input = screen.getByLabelText('Error Field');
      expect(input).toHaveAttribute('aria-invalid', 'true');
      expect(input).toHaveAttribute('aria-describedby', 'error-error');

      const errorMessage = screen.getByText('This field is required');
      expect(errorMessage).toHaveAttribute('id', 'error-error');
      expect(errorMessage).toHaveAttribute('role', 'alert');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should support keyboard navigation and focus management', async () => {
      const user = userEvent.setup();

      const { container } = render(
        <div>
          <FormField
            label="Focus Test Field"
            name="focus"
          />
        </div>
      );

      const input = screen.getByLabelText('Focus Test Field');

      // Test focus behavior
      input.focus();
      expect(input).toHaveFocus();

      // Test typing
      await user.type(input, 'test input');
      expect(input).toHaveValue('test input');

      const results = await axe(container);
      expectNoViolations(results);
    });
  });

  describe('FormError Component', () => {
    it('should have proper ARIA live region attributes', async () => {
      const { container } = render(
        <div>
          <FormError error="Test error message" />
        </div>
      );

      const errorElement = screen.getByRole('alert');
      expect(errorElement).toHaveAttribute('aria-live', 'polite');
      expect(errorElement).toHaveAttribute('aria-atomic', 'true');
      expect(errorElement).toHaveTextContent('Test error message');

      const results = await axe(container);
      expectNoViolations(results);
    });

    it('should not render when no error is provided', () => {
      const { container } = render(
        <div>
          <FormError />
        </div>
      );
      expect(container.querySelector('[role="alert"]')).toBeNull();
    });
  });
});
