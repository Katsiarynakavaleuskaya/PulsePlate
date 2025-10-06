import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";

export default function TabBar() {
  const { pathname } = useLocation();
  const { apiKey } = useAuth();
  const { t } = useTranslation();
  const items = [
    { to: "/", label: "Home", requiresAuth: false },
    { to: "/plate", label: "Plate", requiresAuth: true },
    { to: "/progress", label: "Progress", requiresAuth: true },
    { to: "/profile", label: "Profile", requiresAuth: false },
  ];

  return (
    <nav
      role="tablist"
      aria-label="Main tabs"
      className="fixed bottom-0 inset-x-0 grid grid-cols-4 border-t border-muted/30 bg-navy"
    >
      {items.map(({ to, label, requiresAuth }) => {
        const isDisabled = requiresAuth && !apiKey;
        const isActive = pathname === to;

        if (isDisabled) {
          return (
            <span
              key={to}
              role="tab"
              aria-selected={false}
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
            className={({ isActive }) =>
              `py-3 text-center ${isActive ? "text-primary font-medium" : "text-muted"}`
            }
          >
            {label}
          </NavLink>
        );
      })}
    </nav>
  );
}
