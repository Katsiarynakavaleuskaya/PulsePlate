import fitchefStatic from '../../assets/brand/fitchef-static.png';
import fitchefWink from '../../assets/brand/fitchef-wink.png';

type MascotVariant = 'static' | 'wink';
type MascotSize = 'sm' | 'md' | 'lg';

interface FitChefMascotProps {
  variant?: MascotVariant;
  size?: MascotSize;
  className?: string;
}

const sizeMap: Record<MascotSize, string> = {
  sm: 'h-24 w-24',
  md: 'h-40 w-40',
  lg: 'h-56 w-56',
};

const variantMap: Record<MascotVariant, { src: string; alt: string }> = {
  static: {
    src: fitchefStatic,
    alt: 'FitChef mascot static variant',
  },
  wink: {
    src: fitchefWink,
    alt: 'FitChef mascot wink variant',
  },
};

export function FitChefMascot({
  variant = 'static',
  size = 'md',
  className = '',
}: FitChefMascotProps) {
  const asset = variantMap[variant];

  return (
    <img
      alt={asset.alt}
      className={[sizeMap[size], 'object-contain', className].join(' ').trim()}
      src={asset.src}
    />
  );
}

export default FitChefMascot;
