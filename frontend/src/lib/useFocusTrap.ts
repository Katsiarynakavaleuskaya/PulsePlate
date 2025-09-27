import { useCallback } from "react";

/**
 * Creates a keyboard handler that keeps focus trapped inside the provided container.
 */
export function useFocusTrap(ref: React.RefObject<HTMLElement>) {
  return useCallback(
    (event: React.KeyboardEvent) => {
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

      const focusables = container.querySelectorAll<HTMLElement>(
        'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
      );

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
