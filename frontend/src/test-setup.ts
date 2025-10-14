import { expect } from 'vitest'
import { toHaveNoViolations } from 'jest-axe'

// Extend Vitest matchers with jest-axe
expect.extend(toHaveNoViolations)
