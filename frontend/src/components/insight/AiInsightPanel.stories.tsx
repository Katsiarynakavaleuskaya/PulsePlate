import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import AiInsightPanel from './AiInsightPanel';

const meta: Meta<typeof AiInsightPanel> = {
  title: 'PulsePlate/Patterns/Figma Canon/AI Insight States',
  component: AiInsightPanel,
  parameters: {
    layout: 'centered',
  },
  decorators: [
    (Story) => (
      <div className="w-[24rem] bg-[var(--pp-navy)] p-4">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof AiInsightPanel>;

function InteractivePanel(args: Story['args']): JSX.Element {
  const [query, setQuery] = useState(args?.query ?? '');

  return (
    <AiInsightPanel
      {...args}
      query={query}
      onQueryChange={setQuery}
      onSuggestionClick={setQuery}
      onSubmit={(event) => event.preventDefault()}
    />
  );
}

export const Empty: Story = {
  render: (args) => <InteractivePanel {...args} />,
  args: {
    query: '',
    suggestions: ['Больше белка', 'Сахар меньше', 'План на неделю'],
    subtitle: 'Сформулируйте запрос или выберите подсказку',
  },
};

export const Loading: Story = {
  render: (args) => <InteractivePanel {...args} />,
  args: {
    query: 'Как улучшить ужин сегодня?',
    suggestions: ['Больше белка', 'Сахар меньше', 'План на неделю'],
    subtitle: 'Генерирую рекомендацию…',
    isLoading: true,
  },
};

export const Result: Story = {
  render: (args) => <InteractivePanel {...args} />,
  args: {
    query: 'Как улучшить ужин сегодня?',
    suggestions: ['Больше белка', 'Сахар меньше', 'План на неделю'],
    subtitle: 'Персональная рекомендация на сегодня',
    result: {
      title: 'Совет на ужин',
      body: 'Сегодня вы почти достигли цели по белку. Добавьте 20–30 г белка в ужин: творог или рыбу.',
      confidenceLabel: 'Confidence 0.82',
      tags: ['Last 7 days', 'Meals', 'Goals'],
      primaryActionLabel: 'Применить',
      secondaryActionLabel: 'Подробнее',
    },
  },
};
