import type { JSX } from 'react';
import { Link } from 'react-router-dom';
import { buttonClasses } from '../ui';

interface HomeOpenSetupCtaProps {
  className?: string;
}

export function HomeOpenSetupCta({ className = '' }: HomeOpenSetupCtaProps): JSX.Element {
  return (
    <Link
      to="/setup"
      className={buttonClasses({
        variant: 'primary',
        size: 'lg',
        fullWidth: true,
        className: ['block text-center', className].join(' ').trim(),
      })}
    >
      Configure Setup
    </Link>
  );
}

export default HomeOpenSetupCta;
