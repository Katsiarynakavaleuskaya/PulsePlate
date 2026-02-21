import type { Meta, StoryObj } from '@storybook/react';
import { pageCardStyle } from './pageCardStyle';

type HppCardState = 'default' | 'realtime' | 'fallback' | 'conversion';

interface PageCardStyleDemoProps {
  state: HppCardState;
}

const stateCopy: Record<HppCardState, { label: string; title: string; body: string; accent: string }> = {
  default: {
    label: 'Default',
    title: 'Tokenized page card shell',
    body: 'Baseline card state for static HPP summaries.',
    accent: 'var(--color-primary)',
  },
  realtime: {
    label: 'Realtime',
    title: 'Live signal enabled',
    body: 'Use subtle primary accents while real-time updates stream in.',
    accent: 'var(--color-success)',
  },
  fallback: {
    label: 'Fallback',
    title: 'Realtime unavailable',
    body: 'Keep CTA actionable and present a graceful degraded status.',
    accent: 'var(--color-error)',
  },
  conversion: {
    label: 'Conversion',
    title: 'Upgrade prompt visible',
    body: 'Pair value copy with strong CTA hierarchy in conversion moments.',
    accent: 'var(--pp-gold)',
  },
};

function PageCardStyleDemo({ state }: PageCardStyleDemoProps): JSX.Element {
  const copy = stateCopy[state];

  return (
    <article style={pageCardStyle} className="w-[360px] p-5">
      <div className="h-1 w-full rounded-full" style={{ backgroundColor: copy.accent }} />
      <p className="mt-3 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">{copy.label}</p>
      <h3 className="mt-2 text-lg font-semibold text-[var(--color-text)]">{copy.title}</h3>
      <p className="mt-2 text-sm text-[var(--color-text-muted)]">
        {copy.body}
      </p>
    </article>
  );
}

const meta: Meta<typeof PageCardStyleDemo> = {
  title: 'HPP/PageCardStyle',
  component: PageCardStyleDemo,
};

export default meta;
type Story = StoryObj<typeof PageCardStyleDemo>;

export const Default: Story = {
  args: {
    state: 'default',
  },
};

export const Realtime: Story = {
  args: {
    state: 'realtime',
  },
};

export const Fallback: Story = {
  args: {
    state: 'fallback',
  },
};

export const Conversion: Story = {
  args: {
    state: 'conversion',
  },
};
