import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
}

export function WhoTargetsSkeleton({ className }: SkeletonProps) {
  return (
    <div className={clsx('who-targets-panel__skeleton', className)}>
      <div className="skeleton skeleton--text skeleton--title" />
      <div className="skeleton skeleton--text skeleton--subtitle" />
      <div className="skeleton skeleton--card" />
      <div className="skeleton skeleton--card" />
      <div className="skeleton skeleton--card" />
    </div>
  );
}
