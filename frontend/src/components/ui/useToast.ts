import { useCallback } from 'react';
import toast from 'react-hot-toast';

export const toastUtils = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  info: (message: string) => toast(message),
};

type ToastMethods = {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
};

// Hook version for use in components (avoids hooks rules violations)
export const useToast = (): ToastMethods => {
  return {
    success: useCallback((message: string) => toast.success(message), []),
    error: useCallback((message: string) => toast.error(message), []),
    info: useCallback((message: string) => toast(message), []),
  };
};
