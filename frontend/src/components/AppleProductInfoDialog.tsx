import { useEffect, useId, useRef } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent, Ref } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useFocusTrap } from '../lib/useFocusTrap';
import { Button, Card, CardContent, buttonClasses } from './ui';

interface AppleProductInformationProps {
  descriptionId: string;
  headingId: string;
  headingLevel: 'h1' | 'h2';
  bmiLinkRef?: Ref<HTMLAnchorElement>;
  onDismiss?: () => void;
}

function AppleProductInformation({
  descriptionId,
  headingId,
  headingLevel,
  bmiLinkRef,
  onDismiss,
}: AppleProductInformationProps): JSX.Element {
  const { t } = useTranslation();
  const Heading = headingLevel;

  return (
    <>
      <div className="space-y-4">
        <div className="inline-flex rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-semibold text-[var(--color-primary)]">
          FitChef
        </div>
        <Heading
          id={headingId}
          className="text-2xl font-semibold tracking-tight text-[var(--color-text)] sm:text-3xl"
        >
          {t('appleProduct.title')}
        </Heading>
        <div
          id={descriptionId}
          className="space-y-3 text-sm leading-6 text-[var(--color-text-muted)] sm:text-base"
        >
          <p className="font-medium text-[var(--color-text)]">{t('appleProduct.websiteFree')}</p>
          <p>{t('appleProduct.fitChefDirection')}</p>
          <p>{t('appleProduct.noWebPurchases')}</p>
          <p>{t('appleProduct.storeLinkLater')}</p>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Link
          ref={bmiLinkRef}
          className={buttonClasses({ size: 'md', className: 'justify-center text-center' })}
          to="/bmi"
        >
          {t('appleProduct.tryFreeBmi')}
        </Link>
        <Link
          className={buttonClasses({
            variant: 'secondary',
            size: 'md',
            className: 'justify-center text-center',
          })}
          to="/marketing"
        >
          {t('appleProduct.learnMore')}
        </Link>
        {onDismiss ? (
          <Button className="sm:ml-auto" onClick={onDismiss} variant="ghost">
            {t('appleProduct.notNow')}
          </Button>
        ) : null}
      </div>
    </>
  );
}

export function AppleProductInfoCard(): JSX.Element {
  const headingId = useId();
  const descriptionId = `${headingId}-description`;

  return (
    <Card
      className="w-full max-w-2xl rounded-2xl bg-[var(--color-bg)] shadow-[var(--shadow-lg)]"
      data-testid="apple-product-info-card"
    >
      <CardContent className="p-6 sm:p-8">
        <AppleProductInformation
          descriptionId={descriptionId}
          headingId={headingId}
          headingLevel="h1"
        />
      </CardContent>
    </Card>
  );
}

interface AppleProductInfoDialogProps {
  open: boolean;
  onClose: () => void;
}

export function AppleProductInfoDialog({
  open,
  onClose,
}: AppleProductInfoDialogProps): JSX.Element | null {
  const { t } = useTranslation();
  const headingId = useId();
  const descriptionId = `${headingId}-description`;
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const bmiLinkRef = useRef<HTMLAnchorElement | null>(null);
  const trapFocus = useFocusTrap(dialogRef);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    bmiLinkRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) {
    return null;
  }

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      onClose();
      return;
    }

    trapFocus(event);
  };

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto bg-black/60 p-4"
      role="presentation"
    >
      <div
        ref={dialogRef}
        aria-describedby={descriptionId}
        aria-labelledby={headingId}
        aria-modal="true"
        className="relative w-full max-w-2xl"
        data-testid="apple-product-info-dialog"
        onKeyDown={handleKeyDown}
        role="dialog"
      >
        <Card className="rounded-2xl bg-[var(--color-bg)] shadow-[var(--shadow-xl)]">
          <Button
            aria-label={t('appleProduct.close')}
            className="absolute right-3 top-3 min-h-[44px] min-w-[44px] px-3 text-xl leading-none"
            onClick={onClose}
            variant="ghost"
          >
            <span aria-hidden="true">×</span>
          </Button>
          <CardContent className="p-6 pt-16 sm:p-8 sm:pt-16">
            <AppleProductInformation
              bmiLinkRef={bmiLinkRef}
              descriptionId={descriptionId}
              headingId={headingId}
              headingLevel="h2"
              onDismiss={onClose}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default AppleProductInfoDialog;
