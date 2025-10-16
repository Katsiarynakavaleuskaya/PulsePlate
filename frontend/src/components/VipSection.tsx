import React from 'react';

export interface VipSectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * VIP Section component
 */
export const VipSection: React.FC<VipSectionProps> = ({ title, children, className = "" }) => {
  return (
    <section className={`mb-8 ${className}`}>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        {title}
      </h2>
      {children}
    </section>
  );
};
