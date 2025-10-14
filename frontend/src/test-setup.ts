import { expect } from 'vitest'
import { toHaveNoViolations } from 'jest-axe'
import '@testing-library/jest-dom/vitest'

// Extend Vitest matchers with jest-axe
expect.extend(toHaveNoViolations)
