import type { AriaAttributes } from 'react';

export function hasInvalidState(value: AriaAttributes['aria-invalid'], invalid: boolean | undefined) {
  return invalid || value === true || value === 'true';
}
