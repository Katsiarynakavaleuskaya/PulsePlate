import '@testing-library/jest-dom';
import { toHaveNoViolations } from 'jest-axe';

// Extend Jest matchers with axe accessibility matchers
expect.extend(toHaveNoViolations);

// Configure axe for testing
import { configure } from '@testing-library/react';

// Increase timeout for accessibility tests
configure({ testIdAttribute: 'data-testid' });
