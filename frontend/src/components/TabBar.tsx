import { NavLink, useLocation, matchPath } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";
import { tabRoutes } from "../config/routes";
import { useState, useEffect, useRef } from "react";
import { useVipModule } from "../lib/useFeatureFlag";
import {
  ACTIVE_INDICATOR_CLASS,
  ACTIVE_TAB_CLASS,
  AVAILABLE_TAB_CLASS,
  DISABLED_TAB_BASE_CLASS,
  DISABLED_TAB_FEEDBACK_CLASS,
  DISABLED_TAB_FEEDBACK_MS,
  DISABLED_TAB_ICON_CLASS,
  DISABLED_TAB_LABEL_CLASS,
  DISABLED_TAB_OVERLAY_CLASS,
  getTabBarClass,
} from "./TabBar.helpers";
import { LockKeyhole } from "lucide-react";

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
    }, DISABLED_TAB_FEEDBACK_MS);
  };

  // Calculate number of visible tabs for dynamic grid
  const visibleTabs = tabRoutes.filter(route => !route.requiresVip || isVipEnabled);
  const visibleTabsCount = Math.min(Math.max(visibleTabs.length, 1), 6); // Clamp to 1-6 range


  return (
    <nav
      role="tablist"
      aria-label="Main tabs"
      className={getTabBarClass(visibleTabsCount)}
      data-ui="navigation/tab-bar"
    >
      {visibleTabs.map(({ path: to, label, requiresAuth }) => {
        const isActive = Boolean(matchPath({ path: to, end: to === "/" }, pathname));
        const isDisabled = requiresAuth && !isAuthenticated;
        const isClicked = clickedDisabled === to;

        if (isDisabled) {
          return (
            <div
              key={to}
              className={`${DISABLED_TAB_BASE_CLASS} ${
                isClicked ? 'scale-95' : 'scale-100'
              }`}
              data-feedback={isClicked ? "pressed" : "idle"}
              onClick={() => handleDisabledClick(to)}
              role="tab"
              aria-disabled="true"
              tabIndex={-1}
              title={t("auth.requiresSecureSession")}
            >
              {/* Lock overlay */}
              <div className={DISABLED_TAB_OVERLAY_CLASS}>
                <LockKeyhole aria-hidden="true" className={DISABLED_TAB_ICON_CLASS} />
              </div>

              {/* Label with reduced opacity */}
              <span className={DISABLED_TAB_LABEL_CLASS}>
                {label}
              </span>

              {/* Pulse effect on click */}
              {isClicked && (
                <div
                  className={DISABLED_TAB_FEEDBACK_CLASS}
                  data-testid="tab-disabled-feedback"
                />
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
            className={isActive ? ACTIVE_TAB_CLASS : AVAILABLE_TAB_CLASS}
            data-state={isActive ? "active" : "inactive"}
          >
            {label}

            {/* Active indicator */}
            {isActive && (
              <div
                className={ACTIVE_INDICATOR_CLASS}
                data-testid="tab-active-indicator"
              />
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
