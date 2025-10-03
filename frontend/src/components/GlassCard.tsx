import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";

export type GlassCardTone = "neutral" | "light" | "dark";
export type GlassCardPadding = "none" | "sm" | "md" | "lg";

type GlassCardProps = Omit<HTMLAttributes<HTMLDivElement>, "children" | "className"> & {
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
  neutral: "border border-white/15 bg-white/10 text-white",
  light: "border border-slate-200/80 bg-white/80 text-slate-900",
  dark: "border border-slate-700/70 bg-slate-900/70 text-white",
};

/**
 * RU: Универсальная «стеклянная» карточка под iOS Liquid Glass.
 * EN: Reusable glass-like card (Liquid Glass style).
 */
const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(function GlassCard(
  {
    children,
    className,
    contentClassName,
    padding = "md",
    tone = "neutral",
    role,
    ariaLabel,
    ariaLabelledBy,
    ...rest
  },
  ref
) {
  const ariaProps =
    ariaLabelledBy != null && ariaLabelledBy !== ""
      ? { "aria-labelledby": ariaLabelledBy }
      : ariaLabel
      ? { "aria-label": ariaLabel }
      : {};

  const wrapperClasses = [
    "rounded-2xl",
    "backdrop-blur-xl",
    "shadow-[0_8px_30px_rgba(0,0,0,0.12)]",
    TONE_CLASS[tone],
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const contentClasses = [PADDING_CLASS[padding], contentClassName]
    .filter(Boolean)
    .join(" ");

  const hasAriaContext = "aria-label" in ariaProps || "aria-labelledby" in ariaProps;
  const computedRole = role ?? (hasAriaContext ? "region" : "group");

  return (
    <div ref={ref} className={wrapperClasses} role={computedRole} {...ariaProps} {...rest}>
      <div className={contentClasses}>{children}</div>
    </div>
  );
});

export default GlassCard;
