import React from 'react';

interface EyeIconProps {
  className?: string;
}

export const EyeIcon: React.FC<EyeIconProps> = ({ className = "w-5 h-5" }) => (
  <svg
    width="24"
    height="24"
     viewBox="0 0 24 24"
     fill="none"
     stroke="currentColor"
     strokeWidth="2"
     className={className}
  >
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);
