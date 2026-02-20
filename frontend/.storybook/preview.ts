import type { Preview } from '@storybook/react';
import '../src/styles/tokens.css';
import '../src/index.css';

const preview: Preview = {
  parameters: {
    // Storybook 8 note: keep argTypesRegex for Actions panel only; use explicit fn() handlers in stories/play functions.
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    layout: 'centered',
  },
};

export default preview;
