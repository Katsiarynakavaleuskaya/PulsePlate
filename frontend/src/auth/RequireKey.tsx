import { type ReactNode, useContext } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { AuthContext } from "./AuthContext";

export function RequireKey({ children }: { children: ReactNode }) {
  const auth = useContext(AuthContext);
  const location = useLocation();

  if (!auth?.apiKey) {
    return <Navigate to="/enter-key" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
