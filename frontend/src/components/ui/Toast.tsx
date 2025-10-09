import toast, { Toaster as HotToaster } from 'react-hot-toast';
import { CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react';

export function Toaster() {
  return (
    <HotToaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: 'var(--pp-navy)',
          color: 'var(--pp-text)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        },
        success: {
          icon: <CheckCircle className="w-5 h-5 text-green-400" />,
          style: {
            borderColor: 'rgba(34, 197, 94, 0.3)',
          },
        },
        error: {
          icon: <XCircle className="w-5 h-5 text-red-400" />,
          style: {
            borderColor: 'rgba(239, 68, 68, 0.3)',
          },
        },
        loading: {
          style: {
            borderColor: 'rgba(59, 130, 246, 0.3)',
          },
        },
      }}
    />
  );
}

// Toast functions
export const showSuccess = (message: string) => {
  toast.success(message);
};

export const showError = (message: string) => {
  toast.error(message);
};

export const showInfo = (message: string) => {
  toast(message, {
    icon: <Info className="w-5 h-5 text-blue-400" />,
  });
};

export const showWarning = (message: string) => {
  toast(message, {
    icon: <AlertCircle className="w-5 h-5 text-yellow-400" />,
    style: {
      borderColor: 'rgba(245, 158, 11, 0.3)',
    },
  });
};

export const showLoading = (message: string) => {
  return toast.loading(message);
};

export const dismissToast = (toastId: string) => {
  toast.dismiss(toastId);
};

export const dismissAllToasts = () => {
  toast.dismiss();
};
