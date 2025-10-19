import React, { useState, useRef, useCallback } from 'react';

interface SwipeContainerProps {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  threshold?: number;
  className?: string;
  touchAction?: React.CSSProperties['touchAction'];
}

export function SwipeContainer({
  children,
  onSwipeLeft,
  onSwipeRight,
  threshold = 50,
  className = '',
  touchAction = 'pan-y pinch-zoom',
}: SwipeContainerProps) {
  const [isSwiping, setIsSwiping] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const currentXRef = useRef(0);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touchX = e.touches[0].clientX;
    startXRef.current = touchX;
    currentXRef.current = touchX;
    setIsSwiping(true);
  }, []);

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!isSwiping) return;
      currentXRef.current = e.touches[0].clientX;
    },
    [isSwiping]
  );

  const handleTouchEnd = useCallback(() => {
    if (!isSwiping) return;

    const deltaX = currentXRef.current - startXRef.current;
    const absDeltaX = Math.abs(deltaX);

    // Only trigger swipe if movement is significant enough
    if (absDeltaX > threshold) {
      if (deltaX > 0 && onSwipeRight) {
        onSwipeRight();
      } else if (deltaX < 0 && onSwipeLeft) {
        onSwipeLeft();
      }
    }

    setIsSwiping(false);
  }, [isSwiping, threshold, onSwipeLeft, onSwipeRight]);

  const handleTouchCancel = useCallback(() => {
    setIsSwiping(false);
  }, []);

  return (
    <div
      ref={containerRef}
      className={className}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchCancel}
      style={{ touchAction }}
    >
      {children}
    </div>
  );
}
