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
      const previousAriaHidden = element.getAttribute("aria-hidden");
      element.setAttribute("aria-hidden", "true");
      const focusables = element.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), details, [tabindex]:not([tabindex="-1"]), [contenteditable]:not([contenteditable="false"]), audio[controls], video[controls], iframe'
      );
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
