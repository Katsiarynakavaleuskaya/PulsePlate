import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

export function RequireKey({ children }: { children: ReactNode }) {
  const { apiKey } = useAuth();
  const location = useLocation();

  if (!apiKey) {
    return <Navigate to="/enter-key" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
