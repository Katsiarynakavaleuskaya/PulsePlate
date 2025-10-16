import React from 'react';
import { VipBadge } from './VipBadge';

export interface VipPageHeaderProps {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}

/**
 * VIP Page Header component
 */
export const VipPageHeader: React.FC<VipPageHeaderProps> = ({ title, subtitle, children }) => {
  return (
    <header className="mb-6">
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
        <VipBadge size="lg" />
      </div>
      {subtitle && (
        <p className="text-gray-600 dark:text-gray-400">{subtitle}</p>
      )}
      {children}
    </header>
  );
};
