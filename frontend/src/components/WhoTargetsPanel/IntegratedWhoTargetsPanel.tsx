import { useWhoTargetsWithWeeklyPlan } from '../../hooks/useWhoTargetsWithWeeklyPlan';
import type { TargetsRequest } from '../../api/premium/types';
import type { WeekPlanVM } from '../../features/weekly-plan/model/types';
import { WhoTargetsPanel } from '../WhoTargetsPanel';

interface IntegratedWhoTargetsPanelProps {
  request: TargetsRequest | null;
  onWeeklyPlanGenerated?: (weeklyPlan: WeekPlanVM) => void;
  onError?: (error: Error) => void;
  className?: string;
}

export function IntegratedWhoTargetsPanel({
  request,
  onWeeklyPlanGenerated,
  onError,
  className,
}: IntegratedWhoTargetsPanelProps) {

  const {
    targetsData,
    targetsLoading,
    targetsError,
    weeklyPlanLoading,
    weeklyPlanError,
    saveAndGetWeeklyPlan,
    retry,
  } = useWhoTargetsWithWeeklyPlan({
    onSuccess: (_, weeklyPlan) => {
      onWeeklyPlanGenerated?.(weeklyPlan);
    },
    onError: (error) => {
      onError?.(error);
    },
  });



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
