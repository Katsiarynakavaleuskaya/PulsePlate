import React from 'react';
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { Toggle } from '../ui/Toggle';

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
  });
});
