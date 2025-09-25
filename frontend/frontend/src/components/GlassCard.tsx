import type { ReactNode } from "react";

/**
 * Renders a reusable glass-like container that wraps and visually frames its children.
 *
 * @param children - Content to be rendered inside the card
 * @param className - Optional additional CSS classes to extend or override the card's styling
 * @returns A JSX element: a styled container that frames the provided `children`
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
