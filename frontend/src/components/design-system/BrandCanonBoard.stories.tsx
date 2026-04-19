import type { Meta, StoryObj } from '@storybook/react';
import { BrandCanonBoard } from './CanonBoards';

const meta: Meta<typeof BrandCanonBoard> = {
  title: 'PulsePlate/Patterns/Figma Canon/Brand Canon',
  component: BrandCanonBoard,
};

export default meta;
type Story = StoryObj<typeof BrandCanonBoard>;

export const Default: Story = {};
