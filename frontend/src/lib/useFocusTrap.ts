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

        // Handle radio groups: only the checked/selected radio in a group is focusable
        if (
          (el instanceof HTMLInputElement && el.type === "radio") ||
          (el.getAttribute("role") === "radio")
        ) {
          // For native radios
          if (el instanceof HTMLInputElement && el.name) {
            const radios = document.querySelectorAll<HTMLInputElement>(`input[type="radio"][name="${el.name}"]`);
            if (radios.length > 1) {
              // Only checked radio is focusable
              return el.checked;
            }
          }
          // For ARIA radio groups
          if (el.getAttribute("aria-checked") !== null) {
            return el.getAttribute("aria-checked") === "true";
          }
        }

        // Custom widgets: check for tabindex and ARIA attributes
        const tabIndex = (el as HTMLElement).tabIndex;
        if (tabIndex < 0) return false;
        if ((el as HTMLElement).hasAttribute("aria-disabled") && (el as HTMLElement).getAttribute("aria-disabled") === "true") return false;

        return true;
      };

      // NOTE: isTrulyFocusable does not handle all possible custom widgets or complex composite widgets.
      // It currently supports native form controls, ARIA radio groups, and elements with positive tabindex.
      // Maintainers: If you add new widget types, update isTrulyFocusable accordingly.

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
