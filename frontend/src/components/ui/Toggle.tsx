import React from 'react';

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  description?: string;
  className?: string;
}

export function Toggle({
  label,
  checked,
  onChange,
  disabled = false,
  description,
  className = ''
}: ToggleProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.checked);
  };

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <div className="flex-1">
        <label
          htmlFor={`toggle-${label.replace(/\s+/g, '-').toLowerCase()}`}
          className="text-sm font-medium text-gray-900 dark:text-white cursor-pointer"
        >
          {label}
        </label>
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {description}
          </p>
        )}
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={`toggle-${label.replace(/\s+/g, '-').toLowerCase()}`}
        onClick={() => !disabled && onChange(!checked)}
        disabled={disabled}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
          transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2
          ${checked ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <span
          aria-hidden="true"
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0
            transition duration-200 ease-in-out
            ${checked ? 'translate-x-5' : 'translate-x-0'}
          `}
        />
      </button>

      {/* Hidden checkbox for form compatibility */}
      <input
        id={`toggle-${label.replace(/\s+/g, '-').toLowerCase()}`}
        type="checkbox"
        checked={checked}
        onChange={handleChange}
        disabled={disabled}
        className="sr-only"
        aria-hidden="true"
      />
    </div>
  );
}
