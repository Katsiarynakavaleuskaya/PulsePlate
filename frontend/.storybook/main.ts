import path from 'node:path';
import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(ts|tsx)'],
  addons: ['@storybook/addon-essentials', '@storybook/addon-interactions'],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  async viteFinal(config) {
    config.resolve ??= {};
    config.resolve.alias ??= {};

    if (!Array.isArray(config.resolve.alias)) {
      config.resolve.alias['@'] = path.resolve(__dirname, '../src');
    }

    return config;
  },
};

export default config;
