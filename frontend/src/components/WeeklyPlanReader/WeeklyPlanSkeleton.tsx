import { Skeleton } from '../ui/Skeleton';

interface WeeklyPlanSkeletonProps {
  className?: string;
}

export function WeeklyPlanSkeleton({ className = '' }: WeeklyPlanSkeletonProps) {
  return (
    <div className={`weekly-plan-skeleton ${className}`} data-testid="weekly-plan-skeleton">
      {/* Header skeleton */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-6 w-32" />
        </div>

        {/* Week coverage skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="p-3 rounded-lg bg-gray-100 dark:bg-gray-800">
              <Skeleton className="h-4 w-16 mb-2" />
              <Skeleton className="h-6 w-12" />
            </div>
          ))}
        </div>
      </div>

      {/* Day navigation skeleton */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-10 w-10 rounded-lg" />
        </div>

        {/* Day selector skeleton */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {Array.from({ length: 7 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-20 rounded-lg flex-shrink-0" />
          ))}
        </div>
      </div>

      {/* Day menu skeleton */}
      <div className="space-y-4">
        {/* Meal sections */}
        {Array.from({ length: 3 }).map((_, mealIndex) => (
          <div key={mealIndex} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-4 w-16" />
            </div>

            {/* Meal items */}
            <div className="space-y-2">
              {Array.from({ length: 2 + Math.floor(Math.random() * 3) }).map((_, itemIndex) => (
                <div key={itemIndex} className="flex items-center justify-between">
                  <div className="flex-1">
                    <Skeleton className="h-4 w-3/4 mb-1" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                  <Skeleton className="h-4 w-12" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Shopping list skeleton */}
      <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <Skeleton className="h-6 w-32 mb-3" />
        <Skeleton className="h-4 w-24" />
      </div>
    </div>
  );
}
