import type { Meta, StoryObj } from '@storybook/react';
import { pageCardStyle } from './pageCardStyle';

function PageCardStyleDemo(): JSX.Element {
  return (
    <article style={pageCardStyle} className="w-[360px] p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">HPP Card</p>
      <h3 className="mt-2 text-lg font-semibold text-[var(--color-text)]">Tokenized page card shell</h3>
      <p className="mt-2 text-sm text-[var(--color-text-muted)]">
        This sample verifies border, surface, and radius parity for HPP surfaces.
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

export const Default: Story = {};
