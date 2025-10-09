import type { Preview } from '@storybook/react';
import '../src/index.css';

// Note: I18n setup moved to individual story files because JSX cannot appear in .ts files
// (it requires .tsx extension), so i18n wrappers that use JSX must live in story files.
// See pattern in src/pages/**/*.stories.tsx files, e.g., PlateChart.stories.tsx

export const preview: Preview = {
  parameters: {
    controls: { expanded: true },
    a11y: { element: '#root' },
    docs: {
      toc: true,
    },
    backgrounds: {
      default: 'light',
      values: [
        {
          name: 'light',
          value: '#ffffff',
        },
        {
          name: 'dark',
          value: '#1a1a1a',
        },
        {
          name: 'navy',
          value: '#0F172A',
        },
        {
          name: 'blue',
          value: '#339FFF',
        },
      ],
    },
    viewport: {
      viewports: {
        mobile: {
          name: 'Mobile',
          styles: {
            width: '375px',
            height: '667px',
          },
        },
        tablet: {
          name: 'Tablet',
          styles: {
            width: '768px',
            height: '1024px',
          },
        },
        desktop: {
          name: 'Desktop',
          styles: {
            width: '1440px',
            height: '900px',
          },
        },
      },
    },
  }
};

export default preview;
