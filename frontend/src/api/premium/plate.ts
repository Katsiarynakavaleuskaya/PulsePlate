import { api } from '../client';
import type { PremiumRequestOptions, PlateRequest, PlateApiResponse } from './types';

export const getPlate = (body: PlateRequest, options?: PremiumRequestOptions) =>
  api<PlateApiResponse>(
    '/api/v1/premium/plate',
    { method: 'POST', body: JSON.stringify(body), signal: options?.signal },
    options?.navigate,
    true,
  );

export type { PlateRequest, PlateApiResponse } from './types';
