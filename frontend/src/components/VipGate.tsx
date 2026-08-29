import React, { useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useVipModule } from '../lib/useFeatureFlag';
import { useInert } from '../lib/useInert';
import { AppleProductInfoDialog } from './AppleProductInfoDialog';
import { Card, CardContent, buttonClasses } from './ui';

export interface VipGateProps {
  isVip?: boolean;
  children?: React.ReactNode;
  /** @deprecated Compatibility metadata only; it has no Web acquisition authority. */
  source?: string;
}

export const VipGate: React.FC<VipGateProps> = ({ isVip, children }) => {
  const hookVipStatus = useVipModule();
  const actualIsVip = isVip ?? hookVipStatus;
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();
  const previewRef = useInert(!actualIsVip);
  const describedById = useId();
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const restoreTriggerFocus = (): void => {
    const trigger = triggerRef.current;
    queueMicrotask(() => {
      if (trigger && document.contains(trigger)) {
        trigger.focus();
      }
    });
  };

  const closeInformation = (): void => {
    setOpen(false);
    restoreTriggerFocus();
  };

  if (!children) {
    return (
      <>
        <Card className="mx-auto max-w-xl bg-[var(--color-bg)] text-center shadow-[var(--shadow-sm)]">
          <CardContent className="space-y-4 p-6 sm:p-8">
            <h3 className="text-xl font-semibold text-[var(--color-text)]">
              {t('appleProduct.softHeading')}
            </h3>
            <p className="text-sm leading-6 text-[var(--color-text-muted)]">
              {t('appleProduct.fitChefDirection')}
            </p>
            <button
              ref={triggerRef}
              aria-haspopup="dialog"
              className={buttonClasses({})}
              onClick={() => setOpen(true)}
              type="button"
            >
              {t('appleProduct.learnMore')}
            </button>
          </CardContent>
        </Card>
        <AppleProductInfoDialog onClose={closeInformation} open={open} />
      </>
    );
  }

  if (actualIsVip) {
    return <>{children}</>;
  }

  return (
    <>
      <div ref={previewRef} className="pointer-events-none opacity-60">
        {children}
      </div>

      <p id={describedById} className="sr-only">
        {t('appleProduct.title')} — {t('appleProduct.websiteFree')}
      </p>

      <button
        ref={triggerRef}
        type="button"
        aria-describedby={describedById}
        aria-haspopup="dialog"
        className={buttonClasses({ className: 'mt-3' })}
        onClick={() => setOpen(true)}
      >
        {t('appleProduct.learnMore')}
      </button>

      <AppleProductInfoDialog onClose={closeInformation} open={open} />
    </>
  );
};
