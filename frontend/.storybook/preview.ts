import type { Preview } from '@storybook/react';
import '../src/index.css';

// Note: I18n setup moved to individual story files to avoid JSX in .ts files

export const preview: Preview = {
  parameters: {
    controls: { expanded: true },
    a11y: { element: '#root' },
    docs: {
      toc: true,
    },
  }
};

export default preview;
