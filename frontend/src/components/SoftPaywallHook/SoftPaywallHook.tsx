import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import type { components } from '../../api/schema';
import { Card, CardContent, buttonClasses } from '../ui';

type NextBestAction = components['schemas']['NextBestAction'];

interface SoftPaywallHookProps {
  hook?: components['schemas']['SoftPaywallHook'] | null;
  /**
   * Compatibility input from the BMI response. It is intentionally ignored:
   * server-authored next-step metadata cannot choose Web copy or navigation.
   */
  nextBestAction?: NextBestAction | null;
}

export default function SoftPaywallHook({
  hook,
}: SoftPaywallHookProps): JSX.Element | null {
  const { t } = useTranslation();

  if (!hook?.availability?.pro_available) {
    return null;
  }

  return (
    <Card className="rounded-2xl bg-[var(--color-bg)] shadow-[var(--shadow-sm)]">
      <CardContent className="p-6">
        <h3 className="text-lg font-semibold text-[var(--color-text)]">
          {t('appleProduct.softHeading')}
        </h3>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
          {t('appleProduct.websiteFree')}
        </p>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
          {t('appleProduct.fitChefDirection')}
        </p>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
          {t('appleProduct.noWebPurchases')}
        </p>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
          {t('appleProduct.storeLinkLater')}
        </p>
        <Link
          className={buttonClasses({ className: 'mt-5 inline-flex justify-center' })}
          data-testid="soft-paywall-cta"
          to="/marketing"
        >
          {t('appleProduct.learnMore')}
        </Link>
      </CardContent>
    </Card>
  );
}
