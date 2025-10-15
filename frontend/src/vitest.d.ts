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
    }

    interface AsymmetricMatchersContaining {
      toHaveNoViolations(): void;
    }
  }
}

// Extend Vitest's expect interface to include jest-axe matchers
declare module "vitest" {
  interface Assertion<T = any> {
    toHaveNoViolations(): T;
  }

  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}

export {};
