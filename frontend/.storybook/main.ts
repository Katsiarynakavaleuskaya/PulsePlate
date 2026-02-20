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
    const srcAlias = path.resolve(__dirname, '../src');

    if (Array.isArray(config.resolve.alias)) {
      const hasAlias = config.resolve.alias.some((aliasEntry) => {
        if (typeof aliasEntry === 'object' && aliasEntry !== null && 'find' in aliasEntry) {
          return String(aliasEntry.find) === '@';
        }
        return false;
      });
      if (!hasAlias) {
        config.resolve.alias.push({ find: '@', replacement: srcAlias });
      }
    } else {
      config.resolve.alias['@'] = srcAlias;
    }

    return config;
  },
};

export default config;
