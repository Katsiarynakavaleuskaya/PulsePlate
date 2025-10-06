import { useContext } from "react";
import { AuthContext } from "./AuthContext";
import { Navigate, useLocation } from "react-router-dom";

export const RequireKey: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { apiKey } = useContext(AuthContext);
  const loc = useLocation();

  if (!apiKey) {
    // soft-гейтинг: уводим на /enter-key, но сохраняем from
    return <Navigate to="/enter-key" replace state={{ from: loc.pathname }} />;
  }
  return <>{children}</>;
};
