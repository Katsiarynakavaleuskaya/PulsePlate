// RU: API клиент для расчета BMI (FREE tier endpoint)
// EN: API client for BMI calculation (FREE tier endpoint)

import { api } from './client';
import type { components } from './schema';

type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
type BMICalculateResponse = components['schemas']['BMICalculateResponse'];

export interface BMIApiOptions {
  signal?: AbortSignal;
  onAuthError?: (code: number, headers: Headers) => void;
}

/**
 * Calculate BMI via unified engine.
 * FREE tier endpoint (no API key required).
 *
 * @param request - BMI calculation parameters
 * @param options - Optional request options (signal, onAuthError)
 * @returns BMI calculation response with optional soft paywall hook
 */
export async function calculateBMI(
  request: BMICalculateRequest,
  options?: BMIApiOptions
): Promise<BMICalculateResponse> {
  return api<BMICalculateResponse>(
    '/api/v1/bmi/calculate',
    {
      method: 'POST',
      body: request,
      signal: options?.signal,
    },
    options?.onAuthError ? { onAuthError: options.onAuthError } : undefined,
    true // force JSON Content-Type
  );
}

export type { BMICalculateRequest, BMICalculateResponse };
