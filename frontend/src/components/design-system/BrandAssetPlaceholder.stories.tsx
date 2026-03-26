import type { Meta, StoryObj } from '@storybook/react';
import { DesignSystemCanvas } from './shared';
import { BrandAssetPlaceholder } from './CanonBoards';

const meta: Meta<typeof BrandAssetPlaceholder> = {
  title: 'PulsePlate/Patterns/Figma Canon/Asset Placeholder',
  component: BrandAssetPlaceholder,
  render: (args) => (
    <DesignSystemCanvas>
      <div className="flex min-h-[280px] items-center justify-center rounded-[28px] border border-white/10 bg-white/[0.04] p-8">
        <BrandAssetPlaceholder
          {...args}
          className={['h-[180px] w-[180px]', args.className].filter(Boolean).join(' ')}
        />
      </div>
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof BrandAssetPlaceholder>;

export const Default: Story = {};
