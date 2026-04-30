import path from 'node:path';
import type { StorybookConfig } from '@storybook/react-vite';
import type { OutputOptions } from 'rollup';

const PREMIUM_API_CHUNK = 'premium-api';
type ManualChunksMap = Record<string, readonly string[]>;

function storybookManualChunks(id: string): string | undefined {
  return id.includes('/src/api/premium/') ? PREMIUM_API_CHUNK : undefined;
}

function withStorybookManualChunks(output: OutputOptions | OutputOptions[] | undefined) {
  const applyManualChunks = (entry: OutputOptions = {}): OutputOptions => {
    const existingManualChunks = entry.manualChunks;

    return {
      ...entry,
      manualChunks(id, api) {
        const storybookChunk = storybookManualChunks(id);
        if (storybookChunk) {
          return storybookChunk;
        }

        if (typeof existingManualChunks === 'function') {
          return existingManualChunks(id, api);
        }

        if (existingManualChunks && typeof existingManualChunks === 'object') {
          for (const [chunkName, moduleIds] of Object.entries(existingManualChunks as ManualChunksMap)) {
            if (moduleIds.some((moduleId) => id === moduleId || id.endsWith(`/${moduleId}`))) {
              return chunkName;
            }
          }
        }

        return undefined;
      },
    };
  };

  return Array.isArray(output) ? output.map((entry) => applyManualChunks(entry)) : applyManualChunks(output);
}

const config: StorybookConfig = {
  stories: ['../src/**/*.mdx', '../src/**/*.stories.@(ts|tsx)'],
  addons: [
    // Keep addon-actions/addon-interactions out of this lane to avoid
    // reintroducing the Dependabot #117 uuid carrier through Storybook.
    '@storybook/addon-backgrounds',
    '@storybook/addon-controls',
    '@storybook/addon-docs',
    '@storybook/addon-highlight',
    '@storybook/addon-measure',
    '@storybook/addon-outline',
    '@storybook/addon-toolbars',
    '@storybook/addon-viewport',
  ],
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

    config.build ??= {};
    config.build.rollupOptions ??= {};
    config.build.rollupOptions.output = withStorybookManualChunks(
      config.build.rollupOptions.output as OutputOptions | OutputOptions[] | undefined
    );

    return config;
  },
};

export default config;
