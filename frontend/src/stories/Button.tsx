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
  ...props
}: ButtonProps) => {
  const mode = primary ? 'storybook-button--primary' : 'storybook-button--secondary';
  return (
    <button
      type="button"
      className={['storybook-button', `storybook-button--${size}`, mode].join(' ')}
      style={{ ...(backgroundColor && { backgroundColor }), ...(props.style || {}) }}
      onClick={onClick}
      {...props}
    >
      {label}
    </button>
  );
};
