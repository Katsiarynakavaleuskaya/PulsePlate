import { useLayoutEffect, useRef } from "react";

/** Matches interactive descendants we neutralize when `inert` is unsupported. */
const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), details, [tabindex]:not([tabindex="-1"]), [contenteditable]:not([contenteditable="false"]), audio[controls], video[controls], iframe';

type HTMLElementWithInert = HTMLElement & { inert?: boolean };

/**
 * Custom hook for managing inert attribute on DOM elements
 *
 * Provides feature detection for inert support and fallback implementation
 * for browsers that don't support the inert attribute.
 *
 * @param shouldBeInert - Whether the element should be inert
 * @returns A ref to attach to the DOM element
 */
export function useInert(shouldBeInert: boolean = true) {
  const elementRef = useRef<HTMLDivElement | null>(null);

  // useLayoutEffect: apply inert (or fallback) before paint to avoid a frame where
  // the preview is visible but still keyboard-focusable.
  useLayoutEffect(() => {
    const element = elementRef.current;
    if (!element || !shouldBeInert) {
      return;
    }

    // Feature-detect inert support explicitly
    const el = element as HTMLElementWithInert;
    const hasInertSupport =
      "inert" in HTMLElement.prototype || ("inert" in el && typeof el.inert === "boolean");

    if (hasInertSupport) {
      const prevInert = el.inert;
      el.inert = true;
      return () => {
        el.inert = prevInert;
      };
    } else {
      // Fallback: set aria-hidden and remove tabindex from descendants
      const previousAriaHidden = element.getAttribute("aria-hidden");
      element.setAttribute("aria-hidden", "true");
      const focusables = element.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      focusables.forEach((el) => {
        if (el.hasAttribute("tabindex")) {
          el.setAttribute("data-pp-prev-tabindex", el.getAttribute("tabindex") || "");
        } else {
          el.setAttribute("data-pp-tabindex-added", "true");
        }
        el.setAttribute("tabindex", "-1");

        // Disable interactive elements and mark them for restoration
        if ("disabled" in el && !(el as HTMLButtonElement).disabled) {
          (el as HTMLButtonElement).disabled = true;
          el.setAttribute("data-pp-disabled", "true");
        }
      });
      return () => {
        if (previousAriaHidden === null) {
          element.removeAttribute("aria-hidden");
        } else {
          element.setAttribute("aria-hidden", previousAriaHidden);
        }
        const restore = element.querySelectorAll<HTMLElement>(
          '[data-pp-prev-tabindex], [data-pp-tabindex-added], [data-pp-disabled]'
        );
        restore.forEach((el) => {
          const prev = el.getAttribute("data-pp-prev-tabindex");
          if (prev !== null) {
            if (prev === "") {
              el.removeAttribute("tabindex");
            } else {
              el.setAttribute("tabindex", prev);
            }
            el.removeAttribute("data-pp-prev-tabindex");
          }
          if (el.getAttribute("data-pp-tabindex-added") === "true") {
            el.removeAttribute("tabindex");
            el.removeAttribute("data-pp-tabindex-added");
          }
          if (el.getAttribute("data-pp-disabled") === "true") {
            (el as HTMLButtonElement).disabled = false;
            el.removeAttribute("data-pp-disabled");
          }
        });
      };
    }
  }, [shouldBeInert]);

  return elementRef;
}
