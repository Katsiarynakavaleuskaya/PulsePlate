import { useCallback } from "react";
import type { RefObject, KeyboardEvent as ReactKeyboardEvent } from "react";

/**
 * Creates a keyboard handler that keeps focus trapped inside the provided container.
 */
export function useFocusTrap(ref: RefObject<HTMLElement>) {
  return useCallback(
    (event: ReactKeyboardEvent) => {
      if (event.key !== "Tab") {
        return;
      }

      const container = ref.current;
      if (!container) {
        return;
      }

      if (typeof document === "undefined") {
        return;
      }

      const candidates = container.querySelectorAll<HTMLElement>(
        'a[href], area[href], button, textarea, input, select, [contenteditable="true"], details, summary, audio[controls], video[controls], [tabindex]:not([tabindex="-1"])'
      );

      const isTrulyFocusable = (el: HTMLElement): boolean => {
        if (el.getAttribute("aria-hidden") === "true") return false;
        if (el.tabIndex === -1) return false;
        if ((el as HTMLButtonElement | HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).disabled === true)
          return false;
        if (typeof el.getClientRects === "function" && el.getClientRects().length === 0) return false;
        const style = getComputedStyle(el);
        if (style.visibility === "hidden") return false;
        if (el.offsetParent === null && style.position !== "fixed" && style.position !== "absolute") return false;
        return true;
      };

      const focusables = Array.from(candidates).filter(isTrulyFocusable);

      if (focusables.length === 0) {
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (active === first) {
          event.preventDefault();
          last.focus();
        }
        return;
      }

      if (active === last) {
        event.preventDefault();
        first.focus();
      }
    },
    [ref]
  );
}
