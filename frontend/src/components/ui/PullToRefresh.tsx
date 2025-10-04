import React, { useState, useRef, useCallback } from 'react';
import { RefreshCw, ArrowDown } from 'lucide-react';

interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
  className?: string;
  threshold?: number;
  disabled?: boolean;
}

export function PullToRefresh({
  onRefresh,
  children,
  className = '',
  threshold = 80,
  disabled = false
}: PullToRefreshProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [startY, setStartY] = useState(0);
  const [isPulling, setIsPulling] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (disabled || isRefreshing) return;
    setStartY(e.touches[0].clientY);
    setIsPulling(true);
  }, [disabled, isRefreshing]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isPulling || disabled || isRefreshing) return;

    const currentY = e.touches[0].clientY;
    const distance = Math.max(0, currentY - startY);

    // Only allow pulling when at the top of the container
    if (containerRef.current && containerRef.current.scrollTop === 0) {
      setPullDistance(distance * 0.5); // Dampen the pull distance
    }
  }, [isPulling, startY, disabled, isRefreshing]);

  const handleTouchEnd = useCallback(async () => {
    if (!isPulling || disabled || isRefreshing) {
      setPullDistance(0);
      setIsPulling(false);
      return;
    }

    setIsPulling(false);

    if (pullDistance >= threshold) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } catch (error) {
        console.error('Pull to refresh failed:', error);
      } finally {
        setIsRefreshing(false);
      }
    }

    setPullDistance(0);
  }, [isPulling, pullDistance, threshold, onRefresh, disabled, isRefreshing]);

  const progress = Math.min(pullDistance / threshold, 1);
  const showIndicator = pullDistance > 10;

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden ${className}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull indicator */}
      {showIndicator && (
        <div
          className="absolute top-0 left-0 right-0 z-10 flex items-center justify-center py-4 bg-gradient-to-b from-white to-transparent dark:from-gray-900 dark:to-transparent"
          style={{
            transform: `translateY(${Math.max(-40, pullDistance - 60)}px)`,
            opacity: progress
          }}
        >
          <div className="flex items-center gap-3 text-gray-600 dark:text-gray-400">
            {isRefreshing ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <ArrowDown
                className={`w-5 h-5 transition-transform ${progress >= 1 ? 'rotate-180 text-blue-600' : ''}`}
              />
            )}
            <span className="text-sm font-medium">
              {isRefreshing ? 'Refreshing...' : progress >= 1 ? 'Release to refresh' : 'Pull to refresh'}
            </span>
          </div>
        </div>
      )}

      {/* Content with transform for pull effect */}
      <div
        style={{
          transform: `translateY(${Math.max(0, pullDistance - 40)}px)`,
          transition: isPulling ? 'none' : 'transform 0.3s ease-out'
        }}
      >
        {children}
      </div>
    </div>
  );
}
