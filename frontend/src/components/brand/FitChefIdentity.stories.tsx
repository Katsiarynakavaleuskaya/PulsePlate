import type { Meta, StoryObj } from '@storybook/react';
import fitChefHeroStretch from '../../assets/brand/fitchef-hero-stretch-v1.webp';
import { DesignSystemCanvas } from '../design-system/shared';
import { FitChefMascot } from './FitChefMascot';

function FitChefIdentityReview(): JSX.Element {
  return (
    <DesignSystemCanvas>
      <main className="mx-auto grid w-full max-w-5xl gap-8 p-6 text-white">
        <header className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--pp-gold)]">
            FitChef identity roles
          </p>
          <h1 className="mt-3 text-4xl font-semibold">One character, two presentation modes</h1>
          <p className="mt-4 leading-7 text-white/70">
            Photographic FitChef carries editorial context. Illustrated FitChef remains the compact
            interaction guide. Neither presentation changes product capability.
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          <section
            aria-labelledby="fitchef-editorial-role"
            className="rounded-[var(--radius-2xl)] border border-white/10 bg-white/[0.04] p-5"
          >
            <h2 className="text-xl font-semibold" id="fitchef-editorial-role">
              Editorial real
            </h2>
            <p className="mt-2 text-sm leading-6 text-white/60">
              Public Web Hero: contextual, full-frame, static photography.
            </p>
            <img
              alt="FitChef, a tabby cat stretching on an exercise mat"
              className="mt-5 aspect-[4/5] w-full rounded-[var(--radius-2xl)] bg-[var(--pp-navy)] object-contain"
              decoding="async"
              height={1402}
              loading="lazy"
              src={fitChefHeroStretch}
              width={1122}
            />
          </section>

          <section
            aria-labelledby="fitchef-guide-role"
            className="rounded-[var(--radius-2xl)] border border-white/10 bg-white/[0.04] p-5"
          >
            <h2 className="text-xl font-semibold" id="fitchef-guide-role">
              Interaction guide
            </h2>
            <p className="mt-2 text-sm leading-6 text-white/60">
              Daily and weekly choices: compact illustrated states with clear silhouettes.
            </p>
            <div className="mt-5 grid aspect-[4/5] place-items-center rounded-[var(--radius-2xl)] bg-[var(--pp-navy)] p-8">
              <FitChefMascot size="lg" variant="neutral" />
            </div>
          </section>
        </div>

        <aside className="rounded-[var(--radius-2xl)] border border-white/10 bg-white/[0.04] p-5 text-sm leading-6 text-white/65">
          Do not swap these roles implicitly: photography does not enter the illustrated mascot
          variant enum, and the illustrated guide does not replace approved editorial photography.
        </aside>
      </main>
    </DesignSystemCanvas>
  );
}

const meta = {
  title: 'PulsePlate/Brand/FitChef Identity Roles',
  component: FitChefIdentityReview,
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof FitChefIdentityReview>;

export default meta;
type Story = StoryObj<typeof meta>;

export const EditorialAndInteraction: Story = {};
