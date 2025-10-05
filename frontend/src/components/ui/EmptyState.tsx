import React from 'react';
import { FileX, TrendingUp, BarChart3 } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({
  icon: Icon = FileX,
  title,
  description,
  action
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] p-8 text-center">
      <div className="rounded-full bg-gray-100 dark:bg-gray-800 p-4 mb-4">
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
        <button
          onClick={onStartTracking}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Start Tracking
        </button>
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
      action={
        <button
          onClick={onRetry ?? (() => window.location.reload())}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
        >
          Retry
        </button>
      }
    />
  );
}
