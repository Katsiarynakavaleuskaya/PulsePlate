import { useState, useEffect } from 'react';
import { Wifi, WifiOff } from 'lucide-react';

interface OfflineIndicatorProps {
  className?: string;
}

export function OfflineIndicator({ className = '' }: OfflineIndicatorProps) {
  const isBrowser = typeof window !== 'undefined' && typeof navigator !== 'undefined';
  const initialOnline = isBrowser ? navigator.onLine : true;
  const [isOnline, setIsOnline] = useState(initialOnline);
  const [showIndicator, setShowIndicator] = useState(!initialOnline);

  useEffect(() => {
    let hideTimeout: ReturnType<typeof setTimeout> | undefined;

    const clearHideTimeout = () => {
      if (hideTimeout) {
        clearTimeout(hideTimeout);
        hideTimeout = undefined;
      }
    };

    const handleOnline = () => {
      setIsOnline(true);
      setShowIndicator(true);
      // Hide indicator after 3 seconds
      clearHideTimeout();
      hideTimeout = setTimeout(() => setShowIndicator(false), 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowIndicator(true);
      clearHideTimeout();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearHideTimeout();
    };
  }, []);

  if (!showIndicator) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2 rounded-lg shadow-lg transition-all duration-300 ${
        isOnline
          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      } ${className}`}
    >
      {isOnline ? (
        <Wifi className="w-4 h-4" aria-hidden="true" />
      ) : (
        <WifiOff className="w-4 h-4" aria-hidden="true" />
      )}
      <span className="text-sm font-medium">
        {isOnline ? 'Back online' : 'You are offline'}
      </span>
    </div>
  );
}
