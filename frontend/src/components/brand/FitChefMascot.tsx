import fitchefStatic from '../../assets/brand/fitchef-static.png';
import fitchefPortraitNeutral from '../../assets/brand/fitchef-portrait-neutral-v1.png';
import fitchefPortraitSleepy from '../../assets/brand/fitchef-portrait-sleepy-v1.png';
import fitchefPortraitSurprised from '../../assets/brand/fitchef-portrait-surprised-v1.png';
import fitchefPortraitThinking from '../../assets/brand/fitchef-portrait-thinking-v1.png';
import fitchefPortraitWink from '../../assets/brand/fitchef-portrait-wink-v1.png';

type MascotVariant = 'static' | 'wink' | 'neutral' | 'thinking' | 'sleepy' | 'surprised';
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
    src: fitchefPortraitWink,
    alt: 'FitChef mascot wink portrait',
  },
  neutral: {
    src: fitchefPortraitNeutral,
    alt: 'FitChef mascot neutral portrait',
  },
  thinking: {
    src: fitchefPortraitThinking,
    alt: 'FitChef mascot thinking portrait',
  },
  sleepy: {
    src: fitchefPortraitSleepy,
    alt: 'FitChef mascot sleepy portrait',
  },
  surprised: {
    src: fitchefPortraitSurprised,
    alt: 'FitChef mascot surprised portrait',
  },
};

export function FitChefMascot({
  variant = 'static',
  size = 'md',
  className = '',
}: FitChefMascotProps): JSX.Element {
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
