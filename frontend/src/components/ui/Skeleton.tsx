import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={cn('animate-pulse rounded-md bg-gray-300 dark:bg-gray-700', className)} />;
}

export function ChartSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-32" />
      </div>
      <Skeleton className="h-80 w-full rounded-lg" />
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-lg border p-6 shadow-sm space-y-4">
      <Skeleton className="h-6 w-40" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  );
}

export function ProgressPageSkeleton() {
  return (
    <div className="space-y-6 p-4">
      <ChartSkeleton />
      <ChartSkeleton />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  );
}
