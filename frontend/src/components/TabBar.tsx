import { useState, useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../lib/auth";

const tabs = [
  { to: "/", labelKey: "tabs.home", requiresAuth: false },
  { to: "/plate", labelKey: "tabs.plate", requiresAuth: true },
  { to: "/progress", labelKey: "tabs.progress", requiresAuth: true },
  { to: "/profile", labelKey: "tabs.profile", requiresAuth: true },
];

export default function TabBar() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const { apiKey } = useAuth();
  const [clickedDisabled, setClickedDisabled] = useState<string | null>(null);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  const handleDisabledClick = (path: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setClickedDisabled(path);
    timeoutRef.current = window.setTimeout(() => {
      setClickedDisabled(null);
      timeoutRef.current = null;
    }, 300);
  };

  return (
    <nav
      role="tablist"
      aria-label="Main tabs"
      className="fixed bottom-0 inset-x-0 grid grid-cols-4 border-t border-muted/30 bg-navy"
    >
      {tabs.map(({ to, labelKey, requiresAuth }) => {
        const isActive = pathname === to;
        const isDisabled = requiresAuth && !apiKey;
        const isClicked = clickedDisabled === to;

        if (isDisabled) {
          return (
            <div
              key={to}
              className={`relative py-3 text-center cursor-not-allowed transition-all duration-200 ${
                isClicked ? "scale-95" : "scale-100"
              }`}
              onClick={() => handleDisabledClick(to)}
              role="tab"
              aria-disabled="true"
              tabIndex={-1}
            >
              <div className="absolute inset-0 flex items-center justify-center bg-navy/80 rounded-lg backdrop-blur-sm">
                <span className="text-muted/70" aria-hidden="true">🔒</span>
              </div>
              <span className="text-muted/40 font-medium relative z-10">{t(labelKey)}</span>
              {isClicked && (
                <div className="absolute inset-0 bg-primary/20 rounded-lg animate-pulse" aria-hidden="true" />
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
            {t(labelKey)}
            {isActive && (
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-primary rounded-full" />
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}
