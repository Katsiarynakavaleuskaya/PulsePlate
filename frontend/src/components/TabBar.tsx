import { NavLink, useLocation } from "react-router-dom";

export default function TabBar() {
  const { pathname } = useLocation();
  const items = [
    { to: "/", label: "Home" },
    { to: "/plate", label: "Plate" },
    { to: "/progress", label: "Progress" },
    { to: "/profile", label: "Profile" },
  ];
  return (
    <nav
      role="tablist"
      aria-label="Main tabs"
      className="fixed bottom-0 inset-x-0 grid grid-cols-4 border-t border-muted/30 bg-navy"
    >
      {items.map(({ to, label }) => {
        const isActive =
          to === "/" ? pathname === "/" : pathname === to || pathname.startsWith(`${to}/`);
        return (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            role="tab"
            aria-selected={isActive}
            className={`py-3 text-center ${
              isActive ? "text-primary font-medium" : "text-muted"
            }`}
          >
            {label}
          </NavLink>
        );
      })}
    </nav>
  );
}
