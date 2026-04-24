import type { Meta, StoryObj } from '@storybook/react';
import { IOSFoundationTokensBoard } from './CanonBoards';

const meta: Meta<typeof IOSFoundationTokensBoard> = {
  title: 'PulsePlate/Patterns/Figma Canon/iOS Foundation Tokens',
  component: IOSFoundationTokensBoard,
};

export default meta;
type Story = StoryObj<typeof IOSFoundationTokensBoard>;

export const Default: Story = {};
