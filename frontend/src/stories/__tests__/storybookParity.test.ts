import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const frontendRoot = resolve(__dirname, '../../..');

function readFrontend(path: string): string {
  return readFileSync(resolve(frontendRoot, path), 'utf8');
}

describe('PR-8 Storybook parity surfaces', () => {
  it('keeps the Storybook addon split free of the uuid carrier addons', () => {
    const storybookMain = readFrontend('.storybook/main.ts');

    expect(storybookMain).not.toContain('@storybook/addon-actions');
    expect(storybookMain).not.toContain('@storybook/addon-interactions');
    expect(storybookMain).not.toContain('@storybook/addon-essentials');
  });

  it('registers review-only parity stories for implemented product surfaces', () => {
    const productStories = [
      'src/pages/Home.stories.tsx',
      'src/pages/NutritionSetup.stories.tsx',
      'src/pages/Pro/ProPaywallPage.stories.tsx',
      'src/pages/Plate.stories.tsx',
      'src/pages/Progress.stories.tsx',
    ];

    for (const storyPath of productStories) {
      expect(readFrontend(storyPath)).toContain('PulsePlate/Parity Pack/');
    }
  });

  it('documents governed primitive state coverage in Storybook', () => {
    const primitiveStories = [
      'src/components/ui/Button.stories.tsx',
      'src/components/ui/Skeleton.stories.tsx',
      'src/components/ui/EmptyState.stories.tsx',
    ];

    for (const storyPath of primitiveStories) {
      expect(readFrontend(storyPath)).toMatch(/Loading|State|Status|Disabled|Error|Decorative/);
    }
  });

  it('uses local Storybook fixtures instead of live backend URLs', () => {
    const support = readFrontend('src/stories/storybookParitySupport.tsx');

    expect(support).toContain('https://storybook.pulseplate.local');
    expect(support).toContain('setApiClientDependencies');
    expect(support).not.toContain('localhost');
  });
});
