import { createPremiumEndpoint } from './types';
import type { PlateRequest } from './types';
import type { components } from '../schema';

type PlateResponse = components['schemas']['PlateResponse'];

/**
 * Deprecated premium client → canonical PRO route.
 * Kept under premium/* during migration.
 */
export const getPlate = createPremiumEndpoint<PlateRequest, PlateResponse>(
  '/api/v1/pro/nutrition/plate'
);

export type { PlateRequest } from './types';
export type { PlateResponse };
