/**
 * VIP Feature Component
 *
 * Example component that demonstrates VIP feature flag integration.
 * This component will only render when VIP module is enabled.
 */

import { useVipModule } from '../lib/useFeatureFlag';

interface VipFeatureProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * VIP Feature wrapper component
 *
 * @param children - Content to show when VIP is enabled
 * @param fallback - Content to show when VIP is disabled (optional)
 *
 * @example
 * ```typescript
 * <VipFeature fallback={<PremiumGate />}>
 *   <AdvancedAnalytics />
 * </VipFeature>
 * ```
 */
export const VipFeature: React.FC<VipFeatureProps> = ({ children, fallback = null }) => {
  const isVipEnabled = useVipModule();

  if (!isVipEnabled) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

/**
 * VIP Badge component
 *
 * Shows a VIP badge when VIP module is enabled
 */
export const VipBadge: React.FC = () => {
  const isVipEnabled = useVipModule();

  if (!isVipEnabled) {
    return null;
  }

  return (
    <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-full">
      VIP
    </span>
  );
};

/**
 * VIP Gate component
 *
 * Shows a gate message when VIP features are accessed but VIP is disabled
 */
export const VipGate: React.FC<{ message?: string }> = ({
  message = "This feature requires VIP access"
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-16 h-16 mb-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        VIP Feature
      </h3>
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        {message}
      </p>
      <button
        type="button"
        className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:opacity-90 transition-opacity"
        aria-label="Upgrade to VIP access"
        onClick={() => {
          // TODO: Navigate to upgrade page or open upgrade modal
          console.log('Upgrade to VIP clicked');
        }}
      >
        Upgrade to VIP
      </button>
    </div>
  );
};
