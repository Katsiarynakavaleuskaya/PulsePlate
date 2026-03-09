/**
 * Weekly Plan Hook
 *
 * Provides type-safe access to weekly plan data with automatic normalization.
 * Uses standard React hooks pattern (useState + useEffect) for consistency with existing codebase.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { getWeeklyPlan } from '../../../api/premium/weekly-plan';
import type { ProWeekPlanRequest } from '../../../api/premium/weekly-plan';
import { normalizeWeekPlan } from '../model/adapter';
import type { WeekPlanVM } from '../model/types';

export interface UseWeeklyPlanOptions {
  /** User targets for meal plan generation */
  targets: ProWeekPlanRequest | null;
  /** Enable/disable query */
  enabled?: boolean;
  /** Callback on successful fetch */
  onSuccess?: (data: WeekPlanVM) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseWeeklyPlanReturn {
  data: WeekPlanVM | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  clearData: () => void;
}

/**
 * Fetch and normalize weekly meal plan
 *
 * @example
 * ```tsx
 * const { data, loading, error, refetch } = useWeeklyPlan({
 *   targets: { sex: 'female', age: 30, height_cm: 165, weight_kg: 60, activity: 'moderate', goal: 'maintain' }
 * });
 * ```
 */
export function useWeeklyPlan(options: UseWeeklyPlanOptions): UseWeeklyPlanReturn {
  const { targets, enabled = true, onSuccess, onError } = options;

  const [data, setData] = useState<WeekPlanVM | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const requestIdRef = useRef(0);

  const fetchData = useCallback(async () => {
    if (!targets || !enabled) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    const requestId = ++requestIdRef.current;

    setLoading(true);
    setError(null);

    try {
      const rawResponse = await getWeeklyPlan(targets);

      // Ignore late responses (prevents state updates after a newer request)
      if (requestId !== requestIdRef.current) {
        return;
      }

      // Normalize to view model (adapter handles type coercion and validation)
      const normalized = normalizeWeekPlan(rawResponse);

      setData(normalized);
      onSuccess?.(normalized);
    } catch (err) {
      // Ignore errors from cancelled requests
      if (requestId !== requestIdRef.current) {
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch weekly plan';
      setError(errorMessage);
      onError?.(err instanceof Error ? err : new Error(errorMessage));
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [targets, enabled, onSuccess, onError]);

  useEffect(() => {
    fetchData();
  }, [fetchData, retryKey]);

  const refetch = useCallback(() => {
    setRetryKey((prev) => prev + 1);
  }, []);

  const clearData = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return {
    data,
    loading,
    error,
    refetch,
    clearData,
  };
}
