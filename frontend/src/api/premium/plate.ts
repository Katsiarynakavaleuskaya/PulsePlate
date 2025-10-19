import { createPremiumEndpoint, type PlateRequest, type PlateApiResponse } from './types';

export const getPlate = createPremiumEndpoint<PlateRequest, PlateApiResponse>(
  '/api/v1/premium/plate'
);

export type { PlateRequest, PlateApiResponse } from './types';
