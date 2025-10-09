import type { Preview } from '@storybook/react';
import React from 'react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../src/i18n'; // твоя инициализация i18n
import '../src/index.css';

export const decorators = [
  (Story) => (
    <I18nextProvider i18n={i18n}>
      <Story />
    </I18nextProvider>
  ),
];

const preview: Preview = {
  parameters: {
    controls: { expanded: true },
    a11y: { element: '#root' },
    docs: {
      toc: true,
    },
  }
};

export default preview;
