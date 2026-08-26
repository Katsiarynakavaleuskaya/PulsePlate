import type { Meta, StoryObj } from '@storybook/react';
import type { FitChefSupportHandoffResponse } from '../../api/fitchefSupportHandoff';
import { SupportChoiceCardView, type SupportChoiceViewState } from './SupportChoiceCard';

const DAILY_RESULT: FitChefSupportHandoffResponse = {
  schema_version: 'fitchef_support_handoff.v1',
  scenario: 'support_handoff',
  support_need: 'daily_structure',
  action: {
    action_type: 'handoff_to_product_surface',
    target_surface: 'pro_daily_plate',
  },
  user_confirmation_required: true,
  execution_authority: false,
  plan_mutation_authority: false,
  used_llm: false,
  wellness_boundary: 'wellness_planning_only',
};

const WEEKLY_RESULT: FitChefSupportHandoffResponse = {
  ...DAILY_RESULT,
  support_need: 'weekly_structure',
  action: {
    action_type: 'handoff_to_product_surface',
    target_surface: 'pro_weekly_plan',
  },
};

const idleState: SupportChoiceViewState = {
  status: 'idle',
  selectedNeed: null,
  result: null,
  errorCategory: null,
};

const meta = {
  title: 'PulsePlate/Patterns/FitChef Support Choice',
  component: SupportChoiceCardView,
  args: {
    authState: 'authenticated',
    state: idleState,
    onSelect: () => undefined,
    onSubmit: () => undefined,
    onConfirm: () => undefined,
    onDismiss: () => undefined,
  },
  decorators: [
    (Story) => (
      <div className="min-h-screen w-screen bg-[var(--pp-navy)] p-4 sm:p-8">
        <div className="mx-auto w-full max-w-2xl">
          <Story />
        </div>
      </div>
    ),
  ],
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof SupportChoiceCardView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const IdleNarrow: Story = {
  parameters: { viewport: { defaultViewport: 'mobile1' } },
};

export const ReadyTablet: Story = {
  args: {
    state: {
      status: 'ready',
      selectedNeed: 'daily_structure',
      result: null,
      errorCategory: null,
    },
  },
  parameters: { viewport: { defaultViewport: 'tablet' } },
};

export const PendingDesktop: Story = {
  args: {
    state: {
      status: 'pending',
      selectedNeed: 'weekly_structure',
      result: null,
      errorCategory: null,
    },
  },
  parameters: { viewport: { defaultViewport: 'responsive' } },
};

export const DailyResult: Story = {
  args: {
    state: {
      status: 'success',
      selectedNeed: 'daily_structure',
      result: DAILY_RESULT,
      errorCategory: null,
    },
  },
};

export const WeeklyResult: Story = {
  args: {
    state: {
      status: 'success',
      selectedNeed: 'weekly_structure',
      result: WEEKLY_RESULT,
      errorCategory: null,
    },
  },
};

export const AuthError: Story = {
  args: {
    state: {
      status: 'error',
      selectedNeed: 'daily_structure',
      result: null,
      errorCategory: 'auth_error',
    },
  },
};

export const FeatureUnavailable: Story = {
  args: {
    state: {
      status: 'error',
      selectedNeed: 'weekly_structure',
      result: null,
      errorCategory: 'feature_unavailable',
    },
  },
};

export const NetworkError: Story = {
  args: {
    state: {
      status: 'error',
      selectedNeed: 'daily_structure',
      result: null,
      errorCategory: 'network_error',
    },
  },
};

export const Confirmed: Story = {
  args: {
    state: {
      status: 'confirmed',
      selectedNeed: 'weekly_structure',
      result: WEEKLY_RESULT,
      errorCategory: null,
    },
  },
};

export const Dismissed: Story = {
  args: {
    state: {
      status: 'dismissed',
      selectedNeed: null,
      result: null,
      errorCategory: null,
    },
  },
};
