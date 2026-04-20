import { useAuth } from './AuthContext';
import { Navigate, useLocation } from 'react-router-dom';
import { ReactNode } from 'react';

interface RequireKeyProps {
  children: ReactNode;
}

export const RequireKey: React.FC<RequireKeyProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const loc = useLocation();

  if (isLoading) {
    return (
      <div
        data-testid="auth-bootstrap-state"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="flex min-h-[40vh] items-center justify-center px-6 text-sm font-medium text-[var(--color-text-muted)]"
      >
        Checking secure session...
      </div>
    );
  }

  if (!isAuthenticated) {
    // soft-gating: redirect to /enter-key but preserve the originating path in state for return navigation
    return <Navigate to='/enter-key' replace state={{ from: loc }} />;
  }
  return <>{children}</>;
};
