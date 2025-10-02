import type { HTMLAttributes, ReactNode } from "react";

type GlassCardTone = "neutral" | "light" | "dark";
type GlassCardPadding = "none" | "sm" | "md" | "lg";

type GlassCardProps = {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  padding?: GlassCardPadding;
  tone?: GlassCardTone;
  role?: HTMLAttributes<HTMLDivElement>["role"];
  ariaLabel?: string;
  ariaLabelledBy?: string;
};

const PADDING_CLASS: Record<GlassCardPadding, string> = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

const TONE_CLASS: Record<GlassCardTone, string> = {
  neutral: "border-white/15 bg-white/10 text-white",
  light: "border-slate-200/80 bg-white/80 text-slate-900",
  dark: "border-slate-700/70 bg-slate-900/70 text-white",
};

/**
 * RU: Универсальная «стеклянная» карточка под iOS Liquid Glass.
 * EN: Reusable glass-like card (Liquid Glass style).
 */
export default function GlassCard({
  children,
  className = "",
  contentClassName = "",
  padding = "md",
  tone = "neutral",
  role,
  ariaLabel,
  ariaLabelledBy,
}: GlassCardProps) {
  const ariaProps = {
    ...(ariaLabel ? { "aria-label": ariaLabel } : {}),
    ...(ariaLabelledBy ? { "aria-labelledby": ariaLabelledBy } : {}),
  };

  return (
    <div
      className={`rounded-2xl backdrop-blur-xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] ${TONE_CLASS[tone]} ${className}`.trim()}
      role={role}
      {...ariaProps}
    >
      <div className={`${PADDING_CLASS[padding]} ${contentClassName}`.trim()}>{children}</div>
    </div>
  );
}
