import { useEffect, useRef } from 'react';

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

  useEffect(() => {
    const element = elementRef.current;
    if (!element || !shouldBeInert) {
      return;
    }

    // Feature-detect inert support explicitly
    const hasInertSupport = 'inert' in HTMLElement.prototype ||
                           ('inert' in element && typeof (element as any).inert === 'boolean');

    if (hasInertSupport) {
      // Use native inert when supported
      const prevInert = (element as any).inert;
      (element as any).inert = true;
      return () => {
        (element as any).inert = prevInert;
      };
    } else {
      // Fallback: set aria-hidden and remove tabindex from descendants
      element.setAttribute("aria-hidden", "true");
      const focusables = element.querySelectorAll<HTMLElement>(
        'a, button, input, textarea, select, details, [tabindex]'
      );
      focusables.forEach((el) => {
        if (el.hasAttribute("tabindex")) {
          el.setAttribute("data-pp-prev-tabindex", el.getAttribute("tabindex") || "");
        }
        el.setAttribute("tabindex", "-1");
        if ("disabled" in el && !(el as HTMLButtonElement).disabled) {
          (el as HTMLButtonElement).disabled = true;
          el.setAttribute("data-pp-disabled", "true");
        }
      });
      return () => {
        element.removeAttribute("aria-hidden");
        const restore = element.querySelectorAll<HTMLElement>(
          '[data-pp-prev-tabindex], [tabindex="-1"], [data-pp-disabled]'
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
          } else if (el.getAttribute("tabindex") === "-1") {
            el.removeAttribute("tabindex");
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
