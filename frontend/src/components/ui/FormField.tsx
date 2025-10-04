import React from 'react';
import { FieldError } from 'react-hook-form';

interface FormFieldProps {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  error?: FieldError;
  required?: boolean;
  children?: React.ReactNode;
}

export function FormField({
  label,
  name,
  type = 'text',
  placeholder,
  error,
  required,
  children
}: FormFieldProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor={name}
        className="block text-sm font-medium text-gray-900 dark:text-white"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>

      {React.Children.count(children) > 0 ? children : (
        <input
          id={name}
          name={name}
          type={type}
          placeholder={placeholder}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${name}-error` : undefined}
          aria-required={required ? 'true' : undefined}
          className={`
            w-full px-3 py-2 border rounded-lg shadow-sm
            bg-white dark:bg-gray-800
            border-gray-300 dark:border-gray-600
            text-gray-900 dark:text-white
            placeholder-gray-500 dark:placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            ${error ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : ''}
          `}
        />
      )}

      {error && (
        <p id={`${name}-error`} className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error.message}
        </p>
      )}
    </div>
  );
}

export function FormError({ error }: { error?: string }) {
  if (!error) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
    >
      <div className="flex">
        <div className="ml-3">
          <p className="text-sm text-red-800 dark:text-red-200">
            {error}
          </p>
        </div>
      </div>
    </div>
  );
}
