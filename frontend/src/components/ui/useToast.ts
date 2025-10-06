import toast from 'react-hot-toast';

export function getToastHelpers() {
  return {
    success: (message: string) => toast.success(message),
    error: (message: string) => toast.error(message),
    info: (message: string) => toast(message),
  };
}
