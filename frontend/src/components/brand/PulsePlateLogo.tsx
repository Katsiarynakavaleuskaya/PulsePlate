import brandMark from '../../assets/brand/pulseplate-brand-mark.png';
import ecgLine from '../../assets/brand/ecg-line.svg';

type LogoVariant = 'mark' | 'lockup' | 'compact';
type LogoTone = 'dark' | 'light';

interface PulsePlateLogoProps {
  variant?: LogoVariant;
  tone?: LogoTone;
  className?: string;
}

const markSizes: Record<LogoVariant, string> = {
  mark: 'h-20 w-20',
  lockup: 'h-14 w-14',
  compact: 'h-10 w-10',
};

export function PulsePlateLogo({
  variant = 'lockup',
  tone = 'dark',
  className = '',
}: PulsePlateLogoProps) {
  const isLight = tone === 'light';
  const textColor = isLight ? 'text-[var(--pp-navy)]' : 'text-white';
  const metaColor = isLight ? 'text-[var(--pp-navy)]/55' : 'text-white/55';

  if (variant === 'mark') {
    return (
      <img
        alt="PulsePlate brand mark"
        className={[markSizes.mark, className].join(' ').trim()}
        src={brandMark}
      />
    );
  }

  return (
    <div className={['inline-flex items-center gap-3', className].join(' ').trim()}>
      <img
        alt={variant === 'compact' ? 'PulsePlate compact logo' : 'PulsePlate logo lockup'}
        className={markSizes[variant]}
        src={brandMark}
      />
      <div className="min-w-0">
        <p
          className={[
            'font-semibold tracking-[-0.04em]',
            variant === 'compact' ? 'text-base' : 'text-xl',
            textColor,
          ].join(' ')}
        >
          PulsePlate
        </p>
        <div className="mt-1 flex items-center gap-2">
          <p className="text-[10px] uppercase tracking-[0.28em] text-[var(--pp-gold)]">Wellness</p>
          {variant === 'lockup' ? (
            <img alt="" aria-hidden="true" className="h-2 w-12 opacity-80" src={ecgLine} />
          ) : null}
        </div>
        {variant === 'lockup' ? (
          <p className={['mt-1 text-xs', metaColor].join(' ')}>Always on your Pulse</p>
        ) : null}
      </div>
    </div>
  );
}

export default PulsePlateLogo;
