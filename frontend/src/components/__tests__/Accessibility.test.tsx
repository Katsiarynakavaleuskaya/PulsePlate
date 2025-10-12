import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { vi } from 'vitest';
import { Toggle } from '../ui/Toggle';
import { FormField, FormError } from '../ui/FormField';

describe('Accessibility Tests', () => {
  describe('Toggle Component', () => {
    it('should not have accessibility violations when checked', async () => {
      const { container } = render(
        <Toggle
          label="Test Toggle"
          checked={true}
          onChange={() => {}}
        />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
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
      expect(results).toHaveNoViolations();
    });

    it('should properly associate label with switch using aria-labelledby', async () => {
      const { container } = render(
        <Toggle
          label="Accessibility Test Toggle"
          checked={true}
          onChange={() => {}}
        />
      );
      const switchElement = container.querySelector('[role="switch"]');
      const labelId = switchElement?.getAttribute('aria-labelledby');

      // Verify that aria-labelledby is set and points to a valid element
      expect(labelId).toBeTruthy();
      expect(labelId).toMatch(/^toggle-label-/);

      // Find the label element by its ID
      const label = container.querySelector(`[id="${labelId}"]`);
      expect(label).toBeTruthy();
      expect(label?.textContent).toBe('Accessibility Test Toggle');

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should not have accessibility violations when disabled', async () => {
      const { container } = render(
        <div role="main">
          <Toggle
            label="Disabled Toggle"
            checked={false}
            onChange={() => {}}
            disabled={true}
          />
        </div>
      );

      const switchElement = container.querySelector('[role="switch"]');
      expect(switchElement).toHaveAttribute('disabled');
      expect(switchElement).toHaveClass('cursor-not-allowed');

      const results = await axe(container, {
        rules: {
          'label': { enabled: false } // Disable label rule for hidden inputs
        }
      });
      expect(results).toHaveNoViolations();
    });

    it('should support keyboard navigation and interaction', async () => {
      const user = userEvent.setup();
      const handleChange = vi.fn();

      const { container, rerender } = render(
        <div role="main">
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

      // Test Space key interaction
      await user.keyboard(' ');
      expect(handleChange).toHaveBeenCalledWith(true);

      // Update the component to reflect the new state and test Enter key
      rerender(
        <div role="main">
          <Toggle
            label="Keyboard Test Toggle"
            checked={true}
            onChange={handleChange}
          />
        </div>
      );

      const updatedSwitchElement = screen.getByRole('switch');
      updatedSwitchElement.focus();

      // Test Enter key interaction
      await user.keyboard('{Enter}');
      expect(handleChange).toHaveBeenCalledWith(false);

      const results = await axe(container, {
        rules: {
          'label': { enabled: false } // Disable label rule for hidden inputs
        }
      });
      expect(results).toHaveNoViolations();
    });

    it('should have proper focus management and visible focus styles', async () => {
      const { container } = render(
        <div role="main">
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

      const results = await axe(container, {
        rules: {
          'label': { enabled: false } // Disable label rule for hidden inputs
        }
      });
      expect(results).toHaveNoViolations();
    });

    it('should handle disabled state properly', async () => {
      const { container } = render(
        <div role="main">
          <Toggle
            label="Disabled Focus Test"
            checked={false}
            onChange={() => {}}
            disabled={true}
          />
        </div>
      );

      const disabledSwitch = screen.getByRole('switch');
      expect(disabledSwitch).toHaveAttribute('disabled');
      expect(disabledSwitch).toHaveClass('cursor-not-allowed');

      const results = await axe(container, {
        rules: {
          'label': { enabled: false } // Disable label rule for hidden inputs
        }
      });
      expect(results).toHaveNoViolations();
    });

    it('should have proper ARIA attributes and state management', async () => {
      const { container, rerender } = render(
        <div role="main">
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
        <div role="main">
          <Toggle
            label="ARIA Test Toggle"
            checked={true}
            onChange={() => {}}
          />
        </div>
      );
      expect(switchElement).toHaveAttribute('aria-checked', 'true');

      const results = await axe(container, {
        rules: {
          'label': { enabled: false } // Disable label rule for hidden inputs
        }
      });
      expect(results).toHaveNoViolations();
    });

    it('should pass color contrast accessibility checks', async () => {
      const { container } = render(
        <div role="main">
          <Toggle
            label="Contrast Test Toggle"
            checked={true}
            onChange={() => {}}
          />
        </div>
      );

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
          'label': { enabled: false } // Disable label rule for hidden inputs
        }
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('FormField Component', () => {
    it('should not have accessibility violations with basic input', async () => {
      const { container } = render(
        <div role="main">
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
      expect(results).toHaveNoViolations();
    });

    it('should properly handle required fields and ARIA attributes', async () => {
      const { container } = render(
        <div role="main">
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
      expect(results).toHaveNoViolations();
    });

    it('should properly associate error messages with inputs', async () => {
      const error = { message: 'This field is required', type: 'required' };

      const { container } = render(
        <div role="main">
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
      expect(results).toHaveNoViolations();
    });

    it('should support keyboard navigation and focus management', async () => {
      const user = userEvent.setup();

      const { container } = render(
        <div role="main">
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
      expect(results).toHaveNoViolations();
    });
  });

  describe('FormError Component', () => {
    it('should have proper ARIA live region attributes', async () => {
      const { container } = render(
        <div role="main">
          <FormError error="Test error message" />
        </div>
      );

      const errorElement = screen.getByRole('alert');
      expect(errorElement).toHaveAttribute('aria-live', 'polite');
      expect(errorElement).toHaveAttribute('aria-atomic', 'true');
      expect(errorElement).toHaveTextContent('Test error message');

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should not render when no error is provided', () => {
      const { container } = render(
        <div role="main">
          <FormError />
        </div>
      );
      expect(container.querySelector('[role="alert"]')).toBeNull();
    });
  });
});
