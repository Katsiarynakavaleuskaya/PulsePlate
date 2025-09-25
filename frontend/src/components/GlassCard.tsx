import type { ReactNode } from "react";

/**
 * RU: Универсальная «стеклянная» карточка под iOS Liquid Glass.
 * EN: Reusable glass-like card (Liquid Glass style).
 */
export default function GlassCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-white/15 bg-white/10 backdrop-blur-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] ${className}`}
      role="group"
      aria-label="Content card"
    >
      <div className="p-4">{children}</div>
    </div>
  );
}
