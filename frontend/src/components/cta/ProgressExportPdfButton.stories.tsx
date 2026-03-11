import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { DesignSystemCanvas, PanelShell } from '../design-system/shared';
import { ProgressExportPdfButton } from './ProgressExportPdfButton';

const meta: Meta<typeof ProgressExportPdfButton> = {
  title: 'PulsePlate/Patterns/ProgressExportPdfButton',
  component: ProgressExportPdfButton,
  args: {
    onClick: fn(),
  },
  render: (args) => (
    <DesignSystemCanvas>
      <PanelShell
        title="Web progress utility CTA"
        subtitle="Pilot review surface for web.progress.export_pdf with runtime export affordance."
      >
        <div className="flex justify-end">
          <ProgressExportPdfButton {...args} />
        </div>
      </PanelShell>
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof ProgressExportPdfButton>;

export const Default: Story = {};
