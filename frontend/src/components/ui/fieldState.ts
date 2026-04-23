import type { AriaAttributes } from 'react';

export function hasInvalidState(value: AriaAttributes['aria-invalid'], invalid: boolean | undefined): boolean {
  return Boolean(invalid) || value === true || value === 'true' || value === 'grammar' || value === 'spelling';
}
