import React from 'react';

import './button.css';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Is this the principal call to action on the page? */
  primary?: boolean;
  /** How large should the button be? */
  size?: 'small' | 'medium' | 'large';
  /** Optional background color */
  backgroundColor?: string;
  /** Button contents */
  label: string;
}

/**
 * Primary UI component for user interaction.
 * Note: props.style will override the backgroundColor prop if both are provided.
 */
export const Button = ({
  primary = false,
  size = 'medium',
  backgroundColor,
  label,
  onClick,
  style: externalStyle,
  className: externalClassName,
  ...props
}: ButtonProps) => {
  const mode = primary ? 'storybook-button--primary' : 'storybook-button--secondary';
  const computedClassName = ['storybook-button', `storybook-button--${size}`, mode, externalClassName]
    .filter(Boolean)
    .join(' ');
  return (
    <button
      type="button"
      className={computedClassName}
      style={{ ...(backgroundColor && { backgroundColor }), ...(externalStyle || {}) }}
      onClick={onClick}
      {...props}
    >
      {label}
    </button>
  );
};
