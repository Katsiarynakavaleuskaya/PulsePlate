import React from 'react';
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { Toggle } from '../ui/Toggle';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

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

    it('should not have accessibility violations with custom label', async () => {
      const { container } = render(
        <Toggle
          label="Accessibility Test Toggle"
          checked={true}
          onChange={() => {}}
        />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
