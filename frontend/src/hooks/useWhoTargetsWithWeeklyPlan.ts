import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { getTargets, getWeeklyPlan } from '../api/premium';
import type { TargetsRequest, TargetsApiResponse, WeeklyMenuResponse } from '../api/premium';

interface UseWhoTargetsWithWeeklyPlanOptions {
  onSuccess?: (targets: TargetsApiResponse, weeklyPlan: WeeklyMenuResponse) => void;
  onError?: (error: Error) => void;
}

interface UseWhoTargetsWithWeeklyPlanReturn {
  // Targets state
  targetsData: TargetsApiResponse | null;
  targetsLoading: boolean;
  targetsError: string | null;

  // Weekly plan state
  weeklyPlanData: WeeklyMenuResponse | null;
  weeklyPlanLoading: boolean;
  weeklyPlanError: string | null;

  // Actions
  fetchTargets: (request: TargetsRequest) => Promise<void>;
  saveAndGetWeeklyPlan: (request: TargetsRequest) => Promise<void>;
  retry: () => void;
  clearData: () => void;
}

export function useWhoTargetsWithWeeklyPlan(
  options: UseWhoTargetsWithWeeklyPlanOptions = {}
): UseWhoTargetsWithWeeklyPlanReturn {
  const { t } = useTranslation();
  const { onSuccess, onError } = options;

  // Targets state
  const [targetsData, setTargetsData] = useState<TargetsApiResponse | null>(null);
  const [targetsLoading, setTargetsLoading] = useState(false);
  const [targetsError, setTargetsError] = useState<string | null>(null);

  // Weekly plan state
  const [weeklyPlanData, setWeeklyPlanData] = useState<WeeklyMenuResponse | null>(null);
  const [weeklyPlanLoading, setWeeklyPlanLoading] = useState(false);
  const [weeklyPlanError, setWeeklyPlanError] = useState<string | null>(null);

  // Store the last request for retry functionality
  const [lastRequest, setLastRequest] = useState<TargetsRequest | null>(null);

  const fetchTargets = useCallback(async (request: TargetsRequest) => {
    setLastRequest(request);
    setTargetsLoading(true);
    setTargetsError(null);

    try {
      const response = await getTargets(request);
      setTargetsData(response);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('whoTargets.error.fetchFailed', 'Failed to fetch targets');
      setTargetsError(errorMessage);
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setTargetsLoading(false);
    }
  }, [t, onError]);

  const saveAndGetWeeklyPlan = useCallback(async (request: TargetsRequest) => {
    setLastRequest(request);
    setWeeklyPlanLoading(true);
    setWeeklyPlanError(null);

    try {
      // Always fetch fresh targets to ensure consistency with the request
      setTargetsLoading(true);
      setTargetsError(null);

      let targets: TargetsApiResponse;
      try {
        targets = await getTargets(request);
        setTargetsData(targets);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : t('whoTargets.error.fetchFailed', 'Failed to fetch targets');
        setTargetsError(errorMessage);
        onError?.(error instanceof Error ? error : new Error(errorMessage));
        return; // Exit early without setting weeklyPlanError
      } finally {
        setTargetsLoading(false);
      }

      // Then generate weekly plan
      const weeklyPlan = await getWeeklyPlan(request);
      setWeeklyPlanData(weeklyPlan);

      // Call success callback with both data
      onSuccess?.(targets, weeklyPlan);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('whoTargets.error.weeklyPlanFailed', 'Failed to generate weekly plan');
      setWeeklyPlanError(errorMessage);
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    } finally {
      setWeeklyPlanLoading(false);
    }
  }, [t, onSuccess, onError]);

  const retry = useCallback(() => {
    if (lastRequest) {
      if (targetsError) {
        fetchTargets(lastRequest);
      } else if (weeklyPlanError) {
        saveAndGetWeeklyPlan(lastRequest);
      }
    }
  }, [lastRequest, targetsError, weeklyPlanError, fetchTargets, saveAndGetWeeklyPlan]);

  const clearData = useCallback(() => {
    setTargetsData(null);
    setTargetsError(null);
    setWeeklyPlanData(null);
    setWeeklyPlanError(null);
    setLastRequest(null);
  }, []);

  return {
    // Targets state
    targetsData,
    targetsLoading,
    targetsError,

    // Weekly plan state
    weeklyPlanData,
    weeklyPlanLoading,
    weeklyPlanError,

    // Actions
    fetchTargets,
    saveAndGetWeeklyPlan,
    retry,
    clearData,
  };
}
