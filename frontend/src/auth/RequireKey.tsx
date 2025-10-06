import { useAuth } from './AuthContext';
import { Navigate, useLocation } from 'react-router-dom';
import { ReactNode } from 'react';

interface RequireKeyProps {
  children: ReactNode;
}

export const RequireKey: React.FC<RequireKeyProps> = ({ children }) => {
  const { apiKey } = useAuth();
  const loc = useLocation();

  if (!apiKey) {
    // soft-gating: redirect to /enter-key but preserve the originating path in state for return navigation
    return <Navigate to='/enter-key' replace state={{ from: loc }} />;
  }
  return <>{children}</>;
};
