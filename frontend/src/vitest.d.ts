/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />

import type { AxeResults } from "axe-core";

declare global {
  namespace Vi {
    interface Assertion<T = any> {
      /**
       * Custom matcher from jest-axe for accessibility testing
       *
       * @example
       * const results = await axe(container);
       * expect(results).toHaveNoViolations();
       */
      toHaveNoViolations(): T;
      toHaveNoViolations(results?: AxeResults): T;
    }

    interface AsymmetricMatchersContaining {
      toHaveNoViolations(): void;
    }
  }
}

export {};
