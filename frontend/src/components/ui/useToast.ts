import {
  dismissAllToasts,
  dismissToast,
  showError,
  showInfo,
  showLoading,
  showSuccess,
  showWarning,
} from "./Toast";

export function useToast() {
  return {
    success: showSuccess,
    error: showError,
    info: showInfo,
    warning: showWarning,
    loading: showLoading,
    dismiss: dismissToast,
    dismissAll: dismissAllToasts,
  } as const;
}
