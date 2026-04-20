// RU: Страница PRO paywall - отображает модальное окно с предложением PRO функций
// EN: PRO paywall page - displays modal dialog with PRO feature offer

import { useLocation, useNavigate } from 'react-router-dom';
import BeforeAfter from '../../components/Paywall/BeforeAfter';
import { purchasePremium } from '../../lib/paywallPurchase';

const DEFAULT_PRO_PAYWALL_SOURCE = 'pro_page';
const DEFAULT_PRO_PAYWALL_TRIGGER_REASON = 'unknown';

type ProPaywallLocationState = {
  exposureId?: string;
  source?: string;
  triggerReason?: string;
  via?: string;
  actionType?: string;
  recommendedSurface?: string;
  recommendedTier?: string;
  whyNow?: string;
};

export default function ProPaywallPage(): JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as ProPaywallLocationState | null) ?? null;
  const source = state?.source ?? DEFAULT_PRO_PAYWALL_SOURCE;
  const triggerReason = state?.triggerReason ?? DEFAULT_PRO_PAYWALL_TRIGGER_REASON;
  const via = state?.via ?? 'pro_page';
  const hasNextBestActionContext = Boolean(
    state?.actionType &&
      state?.recommendedSurface &&
      state?.recommendedTier &&
      state?.whyNow
  );

  const handleClose = (): void => {
    navigate(-1); // Go back to previous page
  };

  const handlePurchase = async (): Promise<void> => {
    await purchasePremium({
      source,
      via,
      triggerReason,
      ...(hasNextBestActionContext
        ? {
            actionType: state?.actionType,
            recommendedSurface: state?.recommendedSurface,
            recommendedTier: state?.recommendedTier,
            whyNow: state?.whyNow,
          }
        : {}),
    });
    navigate(-1);
  };

  return (
    <BeforeAfter
      onClose={handleClose}
      onPurchase={handlePurchase}
      initialExposureId={state?.exposureId}
      source={source}
      triggerReason={triggerReason}
      via={via}
    />
  );
}
