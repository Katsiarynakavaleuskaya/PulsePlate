import { NavLink, useLocation, matchPath } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";
import { tabRoutes } from "../config/routes";

export default function TabBar() {
  const { pathname } = useLocation();
  const { apiKey } = useAuth();
  const { t } = useTranslation();

  return (
    <nav
      role="tablist"
      aria-label="Main tabs"
      className="fixed bottom-0 inset-x-0 grid grid-cols-4 border-t border-muted/30 bg-navy"
    >
      {tabRoutes.map(({ path: to, label, requiresAuth }) => {
        const isActive = Boolean(matchPath({ path: to, end: to === "/" }, pathname));
        const isDisabled = requiresAuth && !apiKey;

        if (isDisabled) {
          return (
            <span
              key={to}
              role="tab"
              aria-disabled="true"
              tabIndex={-1}
              className="py-3 text-center text-muted/50 cursor-not-allowed"
              title={t("auth.requiresApiKey")}
            >
              {label}
            </span>
          );
        }

        return (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            role="tab"
            aria-selected={isActive}
            className={`py-3 text-center ${isActive ? "text-primary font-medium" : "text-muted"}`}
          >
            {label}
          </NavLink>
        );
      })}
    </nav>
  );
}
