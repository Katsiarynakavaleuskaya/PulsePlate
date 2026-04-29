import React from 'react';
import { FileX, TrendingUp, BarChart3 } from 'lucide-react';
import { Button } from './Button';

type EmptyStateKind = 'empty' | 'error' | 'loading';

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: React.ReactNode;
  state?: EmptyStateKind;
}

export function EmptyState({
  icon: Icon = FileX,
  title,
  description,
  action,
  state = 'empty',
}: EmptyStateProps) {
  const role = state === 'error' ? 'alert' : 'status';

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[300px] p-8 text-center"
      data-state={state}
      role={role}
      aria-live={state === 'error' ? 'assertive' : 'polite'}
    >
      <div className="rounded-full bg-gray-100 dark:bg-gray-800 p-4 mb-4" aria-hidden="true">
        <Icon className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-md">
        {description}
      </p>
      {action && (
        <div className="mt-2">
          {action}
        </div>
      )}
    </div>
  );
}

export function NoProgressData({ onStartTracking }: { onStartTracking?: () => void }) {
  return (
    <EmptyState
      icon={TrendingUp}
      title="No progress data yet"
      description="Start tracking your health journey to see charts and insights here."
      action={
        onStartTracking ? (
          <Button onClick={onStartTracking}>Start Tracking</Button>
        ) : undefined
      }
    />
  );
}

export function NoChartsAvailable({ onRetry }: { onRetry?: () => void }) {
  return (
    <EmptyState
      icon={BarChart3}
      title="Charts not available"
      description="Unable to load progress charts at the moment. Please try again later."
      state="error"
      action={
        <Button variant="secondary" onClick={onRetry ?? (() => window.location.reload())}>
          Retry
        </Button>
      }
    />
  );
}
