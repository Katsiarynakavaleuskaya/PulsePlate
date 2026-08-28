import React, { useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useInert } from '../lib/useInert';
import { AppleProductInfoDialog } from './AppleProductInfoDialog';
import { buttonClasses } from './ui';

type Props = {
  isPremium: boolean;
  children: React.ReactNode;
  /** @deprecated Compatibility metadata only; it has no Web acquisition authority. */
  source?: string;
  /** @deprecated Compatibility metadata only; it has no Web acquisition authority. */
  paywallSource?: string;
  /** @deprecated Compatibility metadata only; it has no Web acquisition authority. */
  triggerReason?: string;
};

export default function PremiumGate({ isPremium, children }: Props): JSX.Element {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();
  const previewRef = useInert(!isPremium);
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

  if (isPremium) {
    return <>{children}</>;
  }

  return (
    <>
      <div ref={previewRef} className="pointer-events-none opacity-70 saturate-75">
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
}
