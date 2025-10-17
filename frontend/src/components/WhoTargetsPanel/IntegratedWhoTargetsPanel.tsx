import React from 'react';
import { useTranslation } from 'react-i18next';
import { useWhoTargetsWithWeeklyPlan } from '../../hooks/useWhoTargetsWithWeeklyPlan';
import type { TargetsRequest } from '../../api/premium/types';
import { WhoTargetsPanel } from '../WhoTargetsPanel';
import { WhoTargetsSkeleton } from './Skeleton';
import { WhoTargetsErrorState } from './ErrorState';
import { WhoTargetsEmptyState } from './EmptyState';

interface IntegratedWhoTargetsPanelProps {
  request: TargetsRequest | null;
  onWeeklyPlanGenerated?: (weeklyPlan: any) => void;
  onError?: (error: Error) => void;
  className?: string;
}

export function IntegratedWhoTargetsPanel({
  request,
  onWeeklyPlanGenerated,
  onError,
  className,
}: IntegratedWhoTargetsPanelProps) {
  const { t } = useTranslation();

  const {
    targetsData,
    targetsLoading,
    targetsError,
    weeklyPlanData,
    weeklyPlanLoading,
    weeklyPlanError,
    saveAndGetWeeklyPlan,
    retry,
  } = useWhoTargetsWithWeeklyPlan({
    onSuccess: (targets, weeklyPlan) => {
      onWeeklyPlanGenerated?.(weeklyPlan);
    },
    onError: (error) => {
      onError?.(error);
    },
  });

  // Auto-fetch targets when request is provided
  React.useEffect(() => {
    if (request && !targetsData && !targetsLoading) {
      // This would be handled by the parent component or a separate effect
      // For now, we'll rely on the parent to call saveAndGetWeeklyPlan
    }
  }, [request, targetsData, targetsLoading]);

  const handleSaveAndContinue = async () => {
    if (!request) {
      console.error('No request data available for weekly plan generation');
      return;
    }

    try {
      await saveAndGetWeeklyPlan(request);
    } catch (error) {
      console.error('Failed to generate weekly plan:', error);
    }
  };

  const handleRetry = () => {
    retry();
  };

  // Determine the current state
  const isLoading = targetsLoading || weeklyPlanLoading;
  const error = targetsError || weeklyPlanError;

  return (
    <WhoTargetsPanel
      data={targetsData}
      loading={isLoading}
      error={error}
      onSaveAndContinue={request ? handleSaveAndContinue : undefined}
      onRetry={handleRetry}
      className={className}
    />
  );
}
