import { NavLink, useLocation, matchPath } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";
import { tabRoutes } from "../config/routes";
import { useState, useEffect, useRef } from "react";
import { useVipModule } from "../lib/useFeatureFlag";
import { getGridColsClass } from "./TabBar.helpers";

export default function TabBar() {
  const { pathname } = useLocation();
  const { isAuthenticated } = useAuth();
  const { t } = useTranslation();
  const isVipEnabled = useVipModule();
  const [clickedDisabled, setClickedDisabled] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleDisabledClick = (path: string) => {
    // Clear any previous timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setClickedDisabled(path);
    // Show visual feedback for a short time
    timeoutRef.current = setTimeout(() => {
      setClickedDisabled(null);
      timeoutRef.current = null;
    }, 300);
  };

  // Calculate number of visible tabs for dynamic grid
  const visibleTabs = tabRoutes.filter(route => !route.requiresVip || isVipEnabled);
  const visibleTabsCount = Math.min(Math.max(visibleTabs.length, 1), 6); // Clamp to 1-6 range


  return (
    <nav
      role="tablist"
      aria-label="Main tabs"
      className={`fixed bottom-0 inset-x-0 grid ${getGridColsClass(visibleTabsCount)} border-t border-muted/30 bg-navy`}
    >
      {visibleTabs.map(({ path: to, label, requiresAuth }) => {
        const isActive = Boolean(matchPath({ path: to, end: to === "/" }, pathname));
        const isDisabled = requiresAuth && !isAuthenticated;
        const isClicked = clickedDisabled === to;

        if (isDisabled) {
          return (
            <div
              key={to}
              className={`relative py-3 text-center cursor-not-allowed transition-all duration-200 ${
                isClicked ? 'scale-95' : 'scale-100'
              }`}
              onClick={() => handleDisabledClick(to)}
              role="tab"
              aria-disabled="true"
              tabIndex={-1}
              title={t("auth.requiresSecureSession")}
            >
              {/* Lock overlay */}
              <div className="absolute inset-0 flex items-center justify-center bg-navy/80 rounded-lg backdrop-blur-sm">
                <svg
                  className="w-4 h-4 text-muted/70"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
              </div>

              {/* Label with reduced opacity */}
              <span className="text-muted/30 font-medium relative z-10">
                {label}
              </span>

              {/* Pulse effect on click */}
              {isClicked && (
                <div className="absolute inset-0 bg-primary/20 rounded-lg animate-pulse" />
              )}
            </div>
          );
        }

        return (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            role="tab"
            aria-selected={isActive}
            className={`relative py-3 text-center transition-all duration-200 hover:scale-105 ${
              isActive ? "text-primary font-medium" : "text-muted"
            }`}
          >
            {label}

            {/* Active indicator */}
            {isActive && (
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-8 h-0.5 bg-primary rounded-full" />
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
