/** @vitest-environment jsdom */
import { Buffer } from 'node:buffer';
import { createHash } from 'node:crypto';
import {
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { dirname, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import postcss from 'postcss';
import type { Root } from 'postcss';
import { MemoryRouter } from 'react-router-dom';
import * as ts from 'typescript';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PulsePlateMarketingPage from '../../../pages/Marketing/PulsePlateMarketingPage';
import {
  FITCHEF_DEMO_INITIAL_STATE,
  FitChefValueDemo,
  fitChefValueDemoReducer,
} from '../FitChefValueDemo';
import type { FitChefDemoEvent, FitChefDemoState } from '../FitChefValueDemo';

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const componentPath = resolve(currentDirectory, '../FitChefValueDemo.tsx');
const marketingComponentsDirectory = resolve(currentDirectory, '..');
const frontendSourceDirectory = resolve(currentDirectory, '../../..');
const storybookConfigDirectory = resolve(currentDirectory, '../../../../.storybook');
const storybookMainPath = resolve(storybookConfigDirectory, 'main.ts');
const marketingPagePath = resolve(
  currentDirectory,
  '../../../pages/Marketing/PulsePlateMarketingPage.tsx',
);
const routesPath = resolve(currentDirectory, '../../../config/routes.ts');
const marketingStylesPath = resolve(currentDirectory, '../marketing.css');
const marketingTokensPath = resolve(currentDirectory, '../marketing-tokens.css');
const promotedAssetRoot = resolve(frontendSourceDirectory, 'assets/brand/fitchef-public-demo/v1');
const hppTokenGuidelinesPath = resolve(currentDirectory, '../../../stories/HppTokenGuidelines.mdx');
const designSystemGuidelinesPath = resolve(
  currentDirectory,
  '../../../stories/PulsePlateDesignSystemGuidelines.mdx',
);

const excludedSourceDirectories = new Set(['__tests__', '__snapshots__', 'evidence']);

const promotedAssetContract = [
  {
    relativePath: 'activity-palette/endurance.webp',
    width: 410,
    height: 512,
    runtimeBytes: 88776,
    sha256: '09d238901bf22f79525c1b597e1e6cf9b5ce2ceb602f8fa82e9439df7bf998f0', // pragma: allowlist secret
  },
  {
    relativePath: 'activity-palette/movement-everyday-fitness.webp',
    width: 410,
    height: 512,
    runtimeBytes: 94298,
    sha256: '7472fb52b167bed135a76e95f40d681e9962c515d9038a8158611683f436a620', // pragma: allowlist secret
  },
  {
    relativePath: 'activity-palette/strength-power.webp',
    width: 410,
    height: 512,
    runtimeBytes: 33474,
    sha256: '4a154769734dedbbe2ad7fb250e45a371071316971bc27761aee62611c3758d0', // pragma: allowlist secret
  },
  {
    relativePath: 'activity-palette/team-combat.webp',
    width: 410,
    height: 512,
    runtimeBytes: 65154,
    sha256: '80627dd04d4d1ac099e826741e1a10d099ab254bc4e49b45c47b8ae6eb75be8d', // pragma: allowlist secret
  },
  {
    relativePath: 'daily-plate-a-salmon-1024.webp',
    width: 1024,
    height: 1024,
    runtimeBytes: 245002,
    sha256: 'ae1410aeaabf59389ef244cab577ad9d7a82ef5ffc4338ac41f256a034be2149', // pragma: allowlist secret
  },
  {
    relativePath: 'food-context/food-context-ingredients-at-home.webp',
    width: 410,
    height: 512,
    runtimeBytes: 64556,
    sha256: '7759e414df893aea1261e69a84228ebc144f458eeebbee344fb2dd8041b45dfd', // pragma: allowlist secret
  },
  {
    relativePath: 'food-context/food-context-meal-photo.webp',
    width: 410,
    height: 512,
    runtimeBytes: 76426,
    sha256: '579e19094f5b5b3e33df260d7c71199b7c665cf77f7252a61a3b2383fb3fa2a1', // pragma: allowlist secret
  },
  {
    relativePath: 'food-context/food-context-restaurant-chef.webp',
    width: 410,
    height: 512,
    runtimeBytes: 64116,
    sha256: '09dc0969eb4a9fc6e9cf469b5f3a83a075cbad298101ab26602d0ec2ed5725c0', // pragma: allowlist secret
  },
  {
    relativePath: 'food-context/food-context-shopping-stores.webp',
    width: 410,
    height: 512,
    runtimeBytes: 96778,
    sha256: '214a0dcbcfb11caa97a645e1b9b3b66e16da3fc659b0c71c08191c8873441239', // pragma: allowlist secret
  },
  {
    relativePath: 'vip/fitchef-vip-editorial-owner-approved-logo-v2.webp',
    width: 1122,
    height: 1402,
    runtimeBytes: 368238,
    sha256: '324d63729b745d17a0a7706a55bd74979a40a7db8820958a024e4ad73000d8f7', // pragma: allowlist secret
  },
  {
    relativePath: 'weekly-planning-a-meal-grid-1024.webp',
    width: 1024,
    height: 1024,
    runtimeBytes: 332828,
    sha256: '678a55fd171bd40112377e160794019112dee3c1f8e6cb0d29c99f6058380d8a', // pragma: allowlist secret
  },
  {
    relativePath: 'weekly-planning-b-notebook-1024.webp',
    width: 1024,
    height: 1024,
    runtimeBytes: 376662,
    sha256: '8d8f4d53b3f55e323a346520313d5e98021aca94734117e855d1d9b4953fc73d', // pragma: allowlist secret
  },
] as const;

type PromotedAssetContractEntry = (typeof promotedAssetContract)[number];

const idleAssetMarkerMultiset = [
  'activity-palette/endurance.webp',
  'activity-palette/strength-power.webp',
  'activity-palette/team-combat.webp',
  'activity-palette/movement-everyday-fitness.webp',
  'weekly-planning-b-notebook-1024.webp',
  'food-context/food-context-restaurant-chef.webp',
  'food-context/food-context-ingredients-at-home.webp',
  'weekly-planning-a-meal-grid-1024.webp',
  'food-context/food-context-ingredients-at-home.webp',
  'food-context/food-context-restaurant-chef.webp',
  'food-context/food-context-shopping-stores.webp',
  'food-context/food-context-meal-photo.webp',
  'daily-plate-a-salmon-1024.webp',
  'weekly-planning-b-notebook-1024.webp',
  'vip/fitchef-vip-editorial-owner-approved-logo-v2.webp',
].sort();

const forbiddenStaticInteractionSelector = [
  'a',
  'button',
  'input',
  'select',
  'textarea',
  'fieldset',
  'form',
  'details',
  'summary',
  'audio[controls]',
  'video[controls]',
  'iframe',
  'object',
  'embed',
  '[contenteditable]:not([contenteditable="false"])',
  '[role="button"]',
  '[role="link"]',
  '[role="radio"]',
  '[role="group"]',
  '[role="status"]',
  '[aria-live]',
].join(', ');

const frozenWebPChunkSequence = ['VP8X', 'ICCP', 'VP8 '] as const;
const frozenWebPIccProfileBytes = 588;
const frozenWebPIccProfileSha256 =
  '86453c6e1ee138f0be42c75ab37a6d73422df68e4767da1b1d3ae6c05aa20e39'; // pragma: allowlist secret

const promotedAssetDependencies = promotedAssetContract.map(
  ({ relativePath }) => `../../assets/brand/fitchef-public-demo/v1/${relativePath}`,
);
const allowedDemoDependencies = [
  'react',
  '../../assets/brand/fitchef-portrait-neutral-v1.png',
  ...promotedAssetDependencies,
  '../ui/Button',
  '../ui/Card',
  '../ui/RadioGroup',
  './MarketingPrimitives',
].sort();
const forbiddenDependencyFamilyPattern =
  /(^|[/._-])(api|auth|analytics|storage|payment|outcome|provider|rag|llm)([/._-]|$)|SupportChoiceCard/i;

function enumerateModuleDependencies(source: string): string[] {
  return Array.from(
    new Set(
      ts.preProcessFile(source, true, true).importedFiles.map((imported) => imported.fileName),
    ),
  ).sort();
}

function executableLoaderViolations(source: string): string[] {
  const sourceFile = ts.createSourceFile(
    'FitChefValueDemo.fixture.tsx',
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const violations = new Set<string>();

  const visit = (node: ts.Node): void => {
    if (ts.isCallExpression(node)) {
      if (node.expression.kind === ts.SyntaxKind.ImportKeyword) {
        violations.add('dynamic-import-call');
      } else if (ts.isIdentifier(node.expression) && node.expression.text === 'require') {
        violations.add('commonjs-require-call');
      } else if (ts.isPropertyAccessExpression(node.expression)) {
        const callee = node.expression;
        const owner = callee.expression;
        if (
          (callee.name.text === 'glob' || callee.name.text === 'globEager') &&
          ts.isMetaProperty(owner) &&
          owner.keywordToken === ts.SyntaxKind.ImportKeyword &&
          owner.name.text === 'meta'
        ) {
          violations.add('vite-meta-import');
        }
      }
    }
    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
  return Array.from(violations).sort();
}

function dependencyBoundaryViolations(source: string): string[] {
  const allowed = new Set(allowedDemoDependencies);
  const violations = enumerateModuleDependencies(source).flatMap((dependency) => {
    if (forbiddenDependencyFamilyPattern.test(dependency)) {
      return [`forbidden-family:${dependency}`];
    }
    return allowed.has(dependency) ? [] : [`dependency-not-allowed:${dependency}`];
  });

  violations.push(...executableLoaderViolations(source));

  return violations.sort();
}

function cssBoundaryViolations(source: string): string[] {
  const violations = new Set<string>();
  let root: Root;

  if (source.includes('\\')) {
    violations.add('css-escape-not-allowed');
  }

  try {
    root = postcss.parse(source);
  } catch {
    violations.add('css-parse-error');
    return Array.from(violations).sort();
  }

  root.walkAtRules((rule) => {
    if (rule.name.trim().toLowerCase() === 'import') {
      violations.add('css-import');
    }
  });

  const literalRemoteAddressPattern = /(?:https?:\/\/|\/\/)[a-z0-9]/i;
  const comparisonCopyPattern = /\bCandidate\s*Y\b|\bGuided[\s_-]*Reveal\b|\bH2\b/i;
  root.walkDecls((declaration) => {
    if (literalRemoteAddressPattern.test(declaration.value)) {
      violations.add('remote-url');
    }
    if (
      declaration.prop.trim().toLowerCase() === 'content' &&
      comparisonCopyPattern.test(declaration.value)
    ) {
      violations.add('comparison-content');
    }
  });

  return Array.from(violations).sort();
}

function collectRelativeFiles(root: string, relativeDirectory = ''): string[] {
  const directory = resolve(root, relativeDirectory);

  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const relativePath = relativeDirectory ? `${relativeDirectory}/${entry.name}` : entry.name;

      if (entry.isSymbolicLink()) {
        throw new Error(`Asset census rejects symbolic links: ${relativePath}`);
      }
      if (entry.isDirectory()) {
        return collectRelativeFiles(root, relativePath);
      }
      if (!entry.isFile()) {
        throw new Error(`Asset census rejects non-regular entries: ${relativePath}`);
      }

      return [relativePath];
    })
    .sort();
}

function collectVisibleStoryCopy(story: HTMLElement): string[] {
  const nodeFilter = story.ownerDocument.defaultView?.NodeFilter;
  if (!nodeFilter) {
    throw new Error('Story copy census requires a DOM NodeFilter implementation');
  }
  const walker = story.ownerDocument.createTreeWalker(story, nodeFilter.SHOW_TEXT);
  const copy: string[] = [];
  let node = walker.nextNode();

  while (node) {
    const parent = node.parentElement;
    const normalized = node.textContent?.replace(/\s+/g, ' ').trim() ?? '';
    if (normalized && parent && !parent.closest('[aria-hidden="true"], [hidden], script, style')) {
      copy.push(normalized);
    }
    node = walker.nextNode();
  }

  return copy;
}

function collectAssetMarkerMultiset(root: HTMLElement): string[] {
  return Array.from(
    root.querySelectorAll<HTMLImageElement>('img[data-fitchef-asset]'),
    (image) => image.dataset.fitchefAsset ?? '',
  ).sort();
}

function collectStaticInteractionViolations(root: HTMLElement): Element[] {
  const violations = new Set<Element>(root.querySelectorAll(forbiddenStaticInteractionSelector));
  root.querySelectorAll<HTMLElement>('*').forEach((element) => {
    if (element.tabIndex >= 0) {
      violations.add(element);
    }
  });
  return Array.from(violations);
}

function inspectWebP(buffer: Buffer): {
  width: number;
  height: number;
  chunks: string[];
  iccProfileSha256: string;
} {
  if (
    buffer.length < 30 ||
    buffer.toString('ascii', 0, 4) !== 'RIFF' ||
    buffer.toString('ascii', 8, 12) !== 'WEBP'
  ) {
    throw new Error('Invalid or truncated WebP RIFF signature');
  }
  if (buffer.readUInt32LE(4) !== buffer.length - 8) {
    throw new Error('WebP RIFF size must match the complete file');
  }

  const chunks: string[] = [];
  let offset = 12;
  let width: number | null = null;
  let height: number | null = null;
  let iccProfile: Buffer | null = null;

  while (offset < buffer.length) {
    if (offset + 8 > buffer.length) {
      throw new Error('Truncated WebP chunk header');
    }

    const type = buffer.toString('ascii', offset, offset + 4);
    const dataLength = buffer.readUInt32LE(offset + 4);
    const dataOffset = offset + 8;
    const nextOffset = dataOffset + dataLength + (dataLength % 2);

    if (nextOffset > buffer.length) {
      throw new Error(`Truncated WebP chunk: ${type}`);
    }
    if (dataLength % 2 === 1 && buffer[dataOffset + dataLength] !== 0) {
      throw new Error(`WebP chunk padding must be zero: ${type}`);
    }

    chunks.push(type);
    if (type === 'VP8X') {
      if (dataLength !== 10) {
        throw new Error('WebP VP8X canvas header must be exactly 10 bytes');
      }
      if (
        buffer[dataOffset] !== 0x20 ||
        buffer[dataOffset + 1] !== 0 ||
        buffer[dataOffset + 2] !== 0 ||
        buffer[dataOffset + 3] !== 0
      ) {
        throw new Error('WebP VP8X flags must declare only the frozen ICC profile');
      }
      width = buffer.readUIntLE(dataOffset + 4, 3) + 1;
      height = buffer.readUIntLE(dataOffset + 7, 3) + 1;
    } else if (type === 'ICCP') {
      if (dataLength !== frozenWebPIccProfileBytes) {
        throw new Error('WebP ICC profile length does not match the frozen profile');
      }
      iccProfile = Buffer.from(buffer.subarray(dataOffset, dataOffset + dataLength));
    } else if (type === 'VP8 ' && dataLength === 0) {
      throw new Error('WebP VP8 payload must be non-empty');
    }
    offset = nextOffset;
  }

  if (offset !== buffer.length || width === null || height === null || iccProfile === null) {
    throw new Error('WebP must terminate exactly after a VP8X canvas');
  }
  if (chunks.join('|') !== frozenWebPChunkSequence.join('|')) {
    throw new Error('WebP chunk sequence must equal VP8X, ICCP, VP8 exactly once');
  }

  const iccProfileSha256 = createHash('sha256').update(iccProfile).digest('hex');
  if (iccProfileSha256 !== frozenWebPIccProfileSha256) {
    throw new Error('WebP ICC profile hash does not match the frozen sRGB profile');
  }

  return {
    width,
    height,
    chunks,
    iccProfileSha256,
  };
}

interface FixtureWebPChunk {
  type: string;
  payload: Buffer;
}

function readFixtureWebPChunks(buffer: Buffer): FixtureWebPChunk[] {
  const chunks: FixtureWebPChunk[] = [];
  let offset = 12;

  while (offset < buffer.length) {
    const type = buffer.toString('ascii', offset, offset + 4);
    const dataLength = buffer.readUInt32LE(offset + 4);
    const dataOffset = offset + 8;
    chunks.push({
      type,
      payload: Buffer.from(buffer.subarray(dataOffset, dataOffset + dataLength)),
    });
    offset = dataOffset + dataLength + (dataLength % 2);
  }

  return chunks;
}

function buildFixtureWebP(
  chunks: FixtureWebPChunk[],
  {
    paddingByte = 0,
    omitFinalPadding = false,
  }: { paddingByte?: number; omitFinalPadding?: boolean } = {},
): Buffer {
  const parts = chunks.flatMap(({ type, payload }, index) => {
    const header = Buffer.alloc(8);
    header.write(type, 0, 4, 'ascii');
    header.writeUInt32LE(payload.length, 4);
    const needsPadding = payload.length % 2 === 1;
    const omitPadding = omitFinalPadding && index === chunks.length - 1;
    return needsPadding && !omitPadding
      ? [header, payload, Buffer.from([paddingByte])]
      : [header, payload];
  });
  const body = Buffer.concat(parts);
  const header = Buffer.alloc(12);
  header.write('RIFF', 0, 4, 'ascii');
  header.writeUInt32LE(body.length + 4, 4);
  header.write('WEBP', 8, 4, 'ascii');
  return Buffer.concat([header, body]);
}

function collectTypeScriptSources(
  directory: string,
  { excludeStories }: { excludeStories: boolean },
): string[] {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const path = resolve(directory, entry.name);

      if (entry.isDirectory()) {
        return excludedSourceDirectories.has(entry.name)
          ? []
          : collectTypeScriptSources(path, { excludeStories });
      }

      if (!entry.isFile() || !/\.(ts|tsx)$/.test(entry.name)) {
        return [];
      }
      if (/\.(test|spec)\.(ts|tsx)$/.test(entry.name)) {
        return [];
      }
      if (excludeStories && /\.stories\.(ts|tsx)$/.test(entry.name)) {
        return [];
      }

      return [path];
    })
    .sort();
}

function collectStorybookSources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const path = resolve(directory, entry.name);

      if (entry.isDirectory()) {
        return excludedSourceDirectories.has(entry.name) ? [] : collectStorybookSources(path);
      }

      if (!entry.isFile() || !/\.(ts|tsx|mdx)$/.test(entry.name)) {
        return [];
      }
      if (/\.(test|spec)\.(ts|tsx|mdx)$/.test(entry.name)) {
        return [];
      }

      return [path];
    })
    .sort();
}

const marketingProductionModulePaths = collectTypeScriptSources(marketingComponentsDirectory, {
  excludeStories: true,
});
const marketingRuntimeSourcePaths = Array.from(
  new Set([
    ...marketingProductionModulePaths,
    marketingStylesPath,
    marketingTokensPath,
    marketingPagePath,
    routesPath,
  ]),
).sort();
const frontendStorybookSources = collectStorybookSources(frontendSourceDirectory);
const storybookSourcePaths = Array.from(
  new Set([
    ...collectStorybookSources(storybookConfigDirectory),
    ...frontendStorybookSources.filter(
      (path) =>
        /\.stories\.(ts|tsx)$/.test(path) ||
        path.endsWith('.mdx') ||
        path.includes('/src/stories/'),
    ),
  ]),
).sort();
const h2CensusSourcePaths = Array.from(
  new Set([...marketingRuntimeSourcePaths, ...storybookSourcePaths]),
).sort();

const renderMarketingPage = (): ReturnType<typeof render> =>
  render(
    <MemoryRouter>
      <PulsePlateMarketingPage />
    </MemoryRouter>,
  );

afterEach((): void => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

type ProductionStateCaseName<State extends FitChefDemoState> = State extends { status: 'idle' }
  ? 'idle'
  : State extends { status: infer Status extends string; choice: infer Choice extends string }
    ? `${Status}${Capitalize<Choice>}`
    : State extends { status: infer Status extends string }
      ? Status
      : never;

type ProductionEventCaseName<Event extends FitChefDemoEvent> = Event extends {
  type: 'select';
  choice: infer Choice extends string;
}
  ? `select${Capitalize<Choice>}`
  : Event extends { type: infer Type extends string }
    ? Type
    : never;

type DerivedDemoStateName = ProductionStateCaseName<FitChefDemoState>;
type DerivedDemoEventName = ProductionEventCaseName<FitChefDemoEvent>;

const demoStates = {
  idle: FITCHEF_DEMO_INITIAL_STATE,
  selectedToday: { status: 'selected', choice: 'today' },
  selectedWeek: { status: 'selected', choice: 'week' },
  revealedToday: { status: 'revealed', choice: 'today' },
  revealedWeek: { status: 'revealed', choice: 'week' },
} satisfies Record<DerivedDemoStateName, FitChefDemoState>;

const demoEvents = {
  selectToday: { type: 'select', choice: 'today' },
  selectWeek: { type: 'select', choice: 'week' },
  confirm: { type: 'confirm' },
  reset: { type: 'reset' },
} satisfies Record<DerivedDemoEventName, FitChefDemoEvent>;

type DemoStateName = DerivedDemoStateName;
type DemoEventName = DerivedDemoEventName;
type ReferenceExpectation = 'same' | 'new' | 'initial';

const transitionTable: ReadonlyArray<{
  from: DemoStateName;
  event: DemoEventName;
  to: DemoStateName;
  reference: ReferenceExpectation;
}> = [
  { from: 'idle', event: 'selectToday', to: 'selectedToday', reference: 'new' },
  { from: 'idle', event: 'selectWeek', to: 'selectedWeek', reference: 'new' },
  { from: 'idle', event: 'confirm', to: 'idle', reference: 'same' },
  { from: 'idle', event: 'reset', to: 'idle', reference: 'same' },

  { from: 'selectedToday', event: 'selectToday', to: 'selectedToday', reference: 'same' },
  { from: 'selectedToday', event: 'selectWeek', to: 'selectedWeek', reference: 'new' },
  { from: 'selectedToday', event: 'confirm', to: 'revealedToday', reference: 'new' },
  { from: 'selectedToday', event: 'reset', to: 'idle', reference: 'initial' },

  { from: 'selectedWeek', event: 'selectToday', to: 'selectedToday', reference: 'new' },
  { from: 'selectedWeek', event: 'selectWeek', to: 'selectedWeek', reference: 'same' },
  { from: 'selectedWeek', event: 'confirm', to: 'revealedWeek', reference: 'new' },
  { from: 'selectedWeek', event: 'reset', to: 'idle', reference: 'initial' },

  { from: 'revealedToday', event: 'selectToday', to: 'revealedToday', reference: 'same' },
  { from: 'revealedToday', event: 'selectWeek', to: 'selectedWeek', reference: 'new' },
  { from: 'revealedToday', event: 'confirm', to: 'revealedToday', reference: 'same' },
  { from: 'revealedToday', event: 'reset', to: 'idle', reference: 'initial' },

  { from: 'revealedWeek', event: 'selectToday', to: 'selectedToday', reference: 'new' },
  { from: 'revealedWeek', event: 'selectWeek', to: 'revealedWeek', reference: 'same' },
  { from: 'revealedWeek', event: 'confirm', to: 'revealedWeek', reference: 'same' },
  { from: 'revealedWeek', event: 'reset', to: 'idle', reference: 'initial' },
];

describe('FitChef demo reducer', (): void => {
  it('exhaustively covers all five states by all four valid events', (): void => {
    const expectedTransitionPairs = (Object.keys(demoStates) as DemoStateName[])
      .flatMap((from) =>
        (Object.keys(demoEvents) as DemoEventName[]).map((event) => `${from}:${event}`),
      )
      .sort();
    const actualTransitionPairs = transitionTable
      .map(({ from, event }) => `${from}:${event}`)
      .sort();

    expect(actualTransitionPairs).toEqual(expectedTransitionPairs);

    transitionTable.forEach(({ from, event, to, reference }) => {
      const sourceState = demoStates[from];
      const result = fitChefValueDemoReducer(sourceState, demoEvents[event]);

      expect(result).toEqual(demoStates[to]);
      if (reference === 'same') {
        expect(result).toBe(sourceState);
      } else if (reference === 'initial') {
        expect(result).toBe(FITCHEF_DEMO_INITIAL_STATE);
        expect(result).not.toBe(sourceState);
      } else {
        expect(result).not.toBe(sourceState);
      }
    });
  });

  it('fails closed for malformed and unknown event families from every state', (): void => {
    const accessorType = {};
    Object.defineProperty(accessorType, 'type', {
      enumerable: true,
      get: () => {
        throw new Error('type getter must not execute');
      },
    });
    const accessorChoice = { type: 'select' };
    Object.defineProperty(accessorChoice, 'choice', {
      enumerable: true,
      get: () => {
        throw new Error('choice getter must not execute');
      },
    });
    const inheritedReset = Object.create({ type: 'reset' }) as object;
    const inheritedChoice = Object.create({ choice: 'today' }) as { type?: string };
    inheritedChoice.type = 'select';
    const nonEnumerableExtra = { type: 'reset' };
    Object.defineProperty(nonEnumerableExtra, 'extra', { value: true });
    const symbolExtra = { type: 'reset', [Symbol('extra')]: true };
    const nullPrototype = Object.assign(Object.create(null) as object, { type: 'reset' });
    const throwingProxy = new Proxy(
      { type: 'reset' },
      {
        ownKeys: () => {
          throw new Error('ownKeys trap');
        },
      },
    );
    const malformedEvents: unknown[] = [
      undefined,
      null,
      false,
      0,
      '',
      [],
      {},
      { choice: 'today' },
      { type: null },
      { type: 'select' },
      { type: 'select', choice: null },
      { type: 'select', choice: 'month' },
      { type: 'select', choice: 'today', extra: true },
      { type: 'confirm', choice: 'week' },
      { type: 'reset', choice: 'today' },
      { type: 'open' },
      accessorType,
      accessorChoice,
      inheritedReset,
      inheritedChoice,
      nonEnumerableExtra,
      symbolExtra,
      nullPrototype,
      throwingProxy,
      Symbol('unknown-event'),
    ];

    Object.values(demoStates).forEach((state) => {
      malformedEvents.forEach((event) => {
        expect(() => fitChefValueDemoReducer(state, event)).not.toThrow();
        expect(fitChefValueDemoReducer(state, event)).toBe(state);
      });
    });
  });
});

describe('FitChefValueDemo', (): void => {
  it('renders the four approved story families once with exact English copy', () => {
    const { container } = render(<FitChefValueDemo />);
    const root = screen.getByTestId('fitchef-value-demo');
    const storyElements = Array.from(root.querySelectorAll<HTMLElement>('[data-fitchef-story]'));
    const requireStory = (story: string): HTMLElement => {
      const element = root.querySelector<HTMLElement>(`[data-fitchef-story="${story}"]`);

      if (!element) {
        throw new Error(`FitChef story not found: ${story}`);
      }

      return element;
    };
    const approvedStoryCopy = {
      daily: [
        'See how FitChef helps you choose where to start',
        'FitChef shows both options. The choice is yours.',
        'Ways to move',
        'Endurance',
        'Strength & Power',
        'Team & Combat',
        'Movement & Everyday Fitness',
        'Goal',
        'Reduce',
        'Maintain',
        'Gain',
        'Where would you like to start?',
        'Today',
        'Start with the plan for today.',
        'This week',
        'Look at the next seven days.',
        'Confirm choice',
        'Not now',
      ],
      weekly: [
        'A week that changes with you',
        'Starting week',
        'What changed',
        'Your goal changes',
        'A meal out',
        'Use what’s at home',
        'Updated week',
      ],
      'food-context': [
        'A food plan built around real life',
        'Ingredients at home',
        'Restaurant or chef',
        'Shopping and stores',
        'A food photo',
        'One flexible plan',
      ],
      vip: [
        'PulsePlate VIP',
        'Your personal AI nutrition guide',
        'Imagine PulsePlate VIP with FitChef connecting your measurements, goals and routines with everyday action: adapting menus as plans change and suggesting a practical next step when progress slows.',
        'For everyday wellbeing, training, strength and muscle-building goals.',
        'Support to keep you moving forward.',
      ],
    } as const;

    expect(container.querySelectorAll('[data-testid="fitchef-value-demo"]')).toHaveLength(1);
    expect(storyElements.map((story) => story.dataset.fitchefStory)).toEqual([
      'daily',
      'weekly',
      'food-context',
      'vip',
    ]);

    Object.entries(approvedStoryCopy).forEach(([storyName, expectedCopy]) => {
      expect(collectVisibleStoryCopy(requireStory(storyName)), storyName).toEqual([
        ...expectedCopy,
      ]);
    });

    expect(within(root).getByText('Maintain', { exact: true })).toHaveAttribute(
      'aria-current',
      'true',
    );
    expect(within(root).getByText('Reduce', { exact: true })).not.toHaveAttribute('aria-current');
    expect(within(root).getByText('Gain', { exact: true })).not.toHaveAttribute('aria-current');

    const storyWithExtraCopy = requireStory('weekly').cloneNode(true) as HTMLElement;
    const unapprovedCopy = document.createElement('p');
    unapprovedCopy.textContent = 'Internal pipeline state';
    storyWithExtraCopy.append(unapprovedCopy);
    expect(collectVisibleStoryCopy(storyWithExtraCopy)).not.toEqual([...approvedStoryCopy.weekly]);
  });

  it('keeps one H1 control group and reveals the exact Today and Week media', async () => {
    const user = userEvent.setup();
    const { container } = render(<FitChefValueDemo />);
    const demoSection = container.querySelector<HTMLElement>('#fitchef-demo');

    if (!demoSection) {
      throw new Error('FitChef demo section not found');
    }

    const demo = within(demoSection);
    const dailyStory = demoSection.querySelector<HTMLElement>('[data-fitchef-story="daily"]');

    if (!dailyStory) {
      throw new Error('FitChef daily story not found');
    }

    const confirm = demo.getByRole('button', { name: 'Confirm choice' });
    const notNow = demo.getByRole('button', { name: 'Not now' });
    expect(demo.getAllByRole('group', { name: 'Where would you like to start?' })).toHaveLength(1);
    expect(demo.getAllByRole('radio')).toHaveLength(2);
    expect(demo.getAllByRole('button')).toHaveLength(2);
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveClass('ppm-fitchef-confirm');
    expect(notNow).toBeEnabled();
    expect(notNow).toHaveClass('ppm-fitchef-secondary');
    const persistentStatus = within(dailyStory).getByRole('status');
    expect(persistentStatus).toBeEmptyDOMElement();
    expect(persistentStatus).toHaveClass('ppm-fitchef-reveal-card--empty');
    expect(demoSection.querySelectorAll('a')).toHaveLength(0);

    await user.click(demo.getByRole('radio', { name: /Today/ }));
    expect(confirm).toBeEnabled();
    expect(within(dailyStory).getByRole('status')).toBe(persistentStatus);
    expect(persistentStatus).toBeEmptyDOMElement();
    await user.click(confirm);

    const todayResult = within(dailyStory).getByRole('status');
    expect(todayResult).toBe(persistentStatus);
    expect(todayResult).not.toHaveClass('ppm-fitchef-reveal-card--empty');
    expect(within(todayResult).getByRole('heading', { name: 'Daily Plate' })).toBeVisible();
    const todayImage = todayResult.querySelector('img');
    expect(todayImage).toHaveAttribute('data-fitchef-asset', 'daily-plate-a-salmon-1024.webp');
    expect(todayImage?.getAttribute('src')).toMatch(/daily-plate-a-salmon-1024\.webp$/);
    expect(collectAssetMarkerMultiset(demoSection)).toEqual(
      [...idleAssetMarkerMultiset, 'daily-plate-a-salmon-1024.webp'].sort(),
    );
    expect(todayResult).toHaveAttribute('aria-live', 'polite');
    expect(todayResult.querySelector('a, button')).toBeNull();

    await user.click(demo.getByRole('radio', { name: /This week/ }));
    expect(within(dailyStory).getByRole('status')).toBe(persistentStatus);
    expect(persistentStatus).toBeEmptyDOMElement();
    expect(persistentStatus).toHaveClass('ppm-fitchef-reveal-card--empty');
    expect(
      within(dailyStory).queryByRole('heading', { name: 'Daily Plate' }),
    ).not.toBeInTheDocument();
    await user.click(confirm);

    const weekResult = within(dailyStory).getByRole('status');
    expect(within(weekResult).getByRole('heading', { name: 'Weekly Planning' })).toBeVisible();
    const weekImage = weekResult.querySelector('img');
    expect(weekImage).toHaveAttribute(
      'data-fitchef-asset',
      'weekly-planning-a-meal-grid-1024.webp',
    );
    expect(weekImage?.getAttribute('src')).toMatch(/weekly-planning-a-meal-grid-1024\.webp$/);
    expect(collectAssetMarkerMultiset(demoSection)).toEqual(
      [...idleAssetMarkerMultiset, 'weekly-planning-a-meal-grid-1024.webp'].sort(),
    );
    expect(demoSection.querySelectorAll('a')).toHaveLength(0);
  });

  it('keeps Weekly, Food Context, and VIP static and non-live', () => {
    const { container } = render(<FitChefValueDemo />);
    const root = screen.getByTestId('fitchef-value-demo');
    const staticStoryNames = ['weekly', 'food-context', 'vip'] as const;

    staticStoryNames.forEach((storyName) => {
      const story = root.querySelector<HTMLElement>(`[data-fitchef-story="${storyName}"]`);

      if (!story) {
        throw new Error(`Static FitChef story not found: ${storyName}`);
      }

      expect(collectStaticInteractionViolations(story), storyName).toHaveLength(0);
    });

    const foodStory = root.querySelector<HTMLElement>('[data-fitchef-story="food-context"]');
    if (!foodStory) {
      throw new Error('FitChef food-context story not found');
    }
    expect(within(foodStory).getByRole('img', { name: 'Daily Plate example' })).toBeInTheDocument();
    expect(
      within(foodStory).getByRole('img', { name: 'Weekly Planning example' }),
    ).toBeInTheDocument();

    expect(container.querySelectorAll('[data-fitchef-story="daily"] fieldset')).toHaveLength(1);
    expect(
      container.querySelectorAll('[data-fitchef-story]:not([data-fitchef-story="daily"]) fieldset'),
    ).toHaveLength(0);

    const interactiveFixture = document.createElement('div');
    const details = document.createElement('details');
    details.append(document.createElement('summary'));
    const editable = document.createElement('div');
    editable.contentEditable = 'true';
    const tabbable = document.createElement('div');
    tabbable.tabIndex = 0;
    interactiveFixture.append(details, editable, tabbable);
    expect(collectStaticInteractionViolations(interactiveFixture).length).toBeGreaterThanOrEqual(3);
  });

  it('uses every promoted visual exactly from the closed twelve-asset family', () => {
    render(<FitChefValueDemo />);
    const root = screen.getByTestId('fitchef-value-demo');
    const expectedPaths = promotedAssetContract.map(({ relativePath }) => relativePath).sort();
    const runtimeImages = Array.from(root.querySelectorAll<HTMLImageElement>('img'));
    const runtimePaths = runtimeImages
      .map((image) => image.dataset.fitchefAsset)
      .filter((path): path is string => path !== undefined);

    expect(runtimePaths).not.toContain('');
    expect(Array.from(new Set(runtimePaths)).sort()).toEqual(expectedPaths);
    expect(runtimePaths.sort()).toEqual(idleAssetMarkerMultiset);
    runtimeImages.forEach((image) => {
      expect(image).toHaveAttribute('loading', 'lazy');
      expect(image).toHaveAttribute('decoding', 'async');
    });
  });

  it('locks promoted WebP hashes, dimensions, profiles, budgets, and exact membership', () => {
    const expectedPaths = promotedAssetContract.map(({ relativePath }) => relativePath).sort();
    const canonicalAssetRoot = realpathSync(promotedAssetRoot);

    expect(collectRelativeFiles(promotedAssetRoot)).toEqual(expectedPaths);

    promotedAssetContract.forEach(({ relativePath, width, height, runtimeBytes, sha256 }) => {
      const path = resolve(promotedAssetRoot, relativePath);
      const file = lstatSync(path);

      expect(file.isFile(), relativePath).toBe(true);
      expect(file.isSymbolicLink(), relativePath).toBe(false);
      expect(file.size, relativePath).toBe(runtimeBytes);
      expect(
        file.size,
        `${relativePath} must stay within the 500 KiB repository budget`,
      ).toBeLessThanOrEqual(500 * 1024);
      expect(realpathSync(path).startsWith(`${canonicalAssetRoot}${sep}`), relativePath).toBe(true);

      const buffer = readFileSync(path);
      const webp = inspectWebP(buffer);
      expect(createHash('sha256').update(buffer).digest('hex'), relativePath).toBe(sha256);
      expect({ width: webp.width, height: webp.height }, relativePath).toEqual({
        width,
        height,
      });
      expect(webp.chunks, relativePath).toEqual([...frozenWebPChunkSequence]);
      expect(webp.iccProfileSha256, relativePath).toBe(frozenWebPIccProfileSha256);
    });

    const runtimeBytes = promotedAssetContract.reduce(
      (total: number, asset: PromotedAssetContractEntry): number =>
        total + asset.runtimeBytes,
      0,
    );
    const cardBytes = promotedAssetContract
      .filter(
        (asset: PromotedAssetContractEntry): boolean =>
          asset.relativePath.startsWith('activity-palette/') ||
          asset.relativePath.startsWith('food-context/'),
      )
      .reduce(
        (total: number, asset: PromotedAssetContractEntry): number =>
          total + asset.runtimeBytes,
        0,
      );

    expect(runtimeBytes).toBe(1906308);
    expect(cardBytes).toBe(583578);
    expect(cardBytes).toBeLessThanOrEqual(600 * 1024);
  });

  it('fails the asset census closed for unexpected file and directory symlinks', () => {
    const fixtureRoot = mkdtempSync(resolve(tmpdir(), 'pulseplate-fitchef-assets-'));

    try {
      const fileCase = resolve(fixtureRoot, 'file-case');
      const directoryCase = resolve(fixtureRoot, 'directory-case');
      mkdirSync(fileCase);
      mkdirSync(directoryCase);
      const regularFile = resolve(fileCase, 'regular.webp');
      writeFileSync(regularFile, Buffer.from('regular'));
      symlinkSync(regularFile, resolve(fileCase, 'unexpected.webp'), 'file');

      const realDirectory = resolve(directoryCase, 'real');
      mkdirSync(realDirectory);
      symlinkSync(realDirectory, resolve(directoryCase, 'unexpected-directory'), 'dir');

      expect(() => collectRelativeFiles(fileCase)).toThrow(/rejects symbolic links/);
      expect(() => collectRelativeFiles(directoryCase)).toThrow(/rejects symbolic links/);
    } finally {
      rmSync(fixtureRoot, { recursive: true, force: true });
    }
  });

  it('rejects duplicate, unknown, padded, oversized, and truncated WebP carriers', () => {
    const referencePath = resolve(promotedAssetRoot, promotedAssetContract[0].relativePath);
    const reference = readFileSync(referencePath);
    const chunks = readFixtureWebPChunks(reference);
    const [vp8x, iccp, vp8] = chunks;
    if (!vp8x || !iccp || !vp8) {
      throw new Error('Reference WebP must expose the frozen three-chunk profile');
    }
    const animatedVp8x = {
      ...vp8x,
      payload: Buffer.from(vp8x.payload),
    };
    animatedVp8x.payload[0] |= 0x02;
    const oddIccp = { ...iccp, payload: Buffer.concat([iccp.payload, Buffer.from([0])]) };
    const oddVp8 = { ...vp8, payload: Buffer.concat([vp8.payload, Buffer.from([0])]) };
    const oversizedDeclaration = Buffer.from(reference);
    oversizedDeclaration.writeUInt32LE(0xffffffff, 16);

    const rejectedFixtures = [
      buildFixtureWebP([vp8x, vp8x, iccp, vp8]),
      buildFixtureWebP([vp8x, iccp, iccp, vp8]),
      buildFixtureWebP([vp8x, iccp, vp8, { type: 'JUNK', payload: Buffer.alloc(0) }]),
      buildFixtureWebP([animatedVp8x, iccp, vp8]),
      buildFixtureWebP([vp8x, oddIccp, vp8], { paddingByte: 1 }),
      buildFixtureWebP([vp8x, iccp, oddVp8], { omitFinalPadding: true }),
      oversizedDeclaration,
      reference.subarray(0, -1),
      Buffer.concat([reference, Buffer.from([0])]),
    ];

    rejectedFixtures.forEach((fixture) => {
      expect(() => inspectWebP(fixture)).toThrow();
    });
    expect(() => buildFixtureWebP([vp8x, oddIccp, vp8], { paddingByte: 1 })).not.toThrow();
    expect(() => inspectWebP(buildFixtureWebP([vp8x, oddIccp, vp8], { paddingByte: 1 }))).toThrow(
      /padding must be zero/,
    );
  });

  it('clears a revealed result immediately when the choice changes', async () => {
    const user = userEvent.setup();
    const { container } = render(<FitChefValueDemo />);
    const dailyStory = container.querySelector<HTMLElement>('[data-fitchef-story="daily"]');

    if (!dailyStory) {
      throw new Error('FitChef daily story not found');
    }

    await user.click(screen.getByRole('radio', { name: /Today/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(within(dailyStory).getByRole('heading', { name: 'Daily Plate' })).toBeVisible();

    await user.click(screen.getByRole('radio', { name: /This week/ }));

    expect(within(dailyStory).getByRole('status')).toBeEmptyDOMElement();
    expect(within(dailyStory).getByRole('status')).toHaveClass(
      'ppm-fitchef-reveal-card--empty',
    );
    expect(
      within(dailyStory).queryByRole('heading', { name: 'Daily Plate' }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(within(dailyStory).getByRole('heading', { name: 'Weekly Planning' })).toBeVisible();
  });

  it('resets from every interactive state and remounts in idle', async () => {
    const user = userEvent.setup();
    const firstRender = render(<FitChefValueDemo />);
    const notNow = screen.getByRole('button', { name: 'Not now' });

    expect(notNow).toBeEnabled();
    await user.click(notNow);
    await user.click(screen.getByRole('radio', { name: /Today/ }));
    await user.click(notNow);
    screen.getAllByRole('radio').forEach((radio) => expect(radio).not.toBeChecked());

    await user.click(screen.getByRole('radio', { name: /This week/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    await user.click(notNow);
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
    expect(screen.getByRole('status')).toHaveClass('ppm-fitchef-reveal-card--empty');

    firstRender.unmount();
    render(<FitChefValueDemo />);

    expect(screen.getByRole('button', { name: 'Confirm choice' })).toBeDisabled();
    screen.getAllByRole('radio').forEach((radio) => expect(radio).not.toBeChecked());
  });

  it('supports the native keyboard path and exposes non-color selection state', async () => {
    const user = userEvent.setup();
    render(<FitChefValueDemo />);

    const today = screen.getByRole('radio', { name: /Today/ });
    const week = screen.getByRole('radio', { name: /This week/ });

    await user.tab();
    expect(today).toHaveFocus();
    await user.keyboard('[Space]');
    expect(today).toBeChecked();
    expect(today).toHaveAttribute('aria-checked', 'true');
    expect(today.closest('label')).toHaveClass('ppm-fitchef-option--selected');

    await user.keyboard('[ArrowRight]');
    expect(week).toHaveFocus();
    expect(week).toBeChecked();
    expect(week).toHaveAttribute('aria-checked', 'true');
    expect(today).toHaveAttribute('aria-checked', 'false');

    await user.tab();
    expect(screen.getByRole('button', { name: 'Confirm choice' })).toHaveFocus();
    await user.keyboard('[Enter]');
    expect(screen.getByRole('heading', { name: 'Weekly Planning' })).toBeVisible();
  });

  it('has no interaction-handler request, console, storage, analytics, or navigation side effects', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    const xhrSpy = vi.fn();
    const webSocketSpy = vi.fn();
    const indexedDbOpenSpy = vi.fn();
    const indexedDbDeleteSpy = vi.fn();
    const beaconSpy = vi.fn();
    const openSpy = vi.fn();
    const gtagSpy = vi.fn();
    const dataLayerPushSpy = vi.fn();
    const consoleErrorSpy = vi.spyOn(console, 'error');
    const consoleWarnSpy = vi.spyOn(console, 'warn');
    const pushStateSpy = vi.spyOn(window.history, 'pushState');
    const replaceStateSpy = vi.spyOn(window.history, 'replaceState');
    const storageGetSpy = vi.spyOn(Storage.prototype, 'getItem');
    const storageSetSpy = vi.spyOn(Storage.prototype, 'setItem');
    const storageRemoveSpy = vi.spyOn(Storage.prototype, 'removeItem');
    const storageClearSpy = vi.spyOn(Storage.prototype, 'clear');
    const cookieBefore = document.cookie;
    const locationBefore = window.location.href;
    const beaconDescriptor = Object.getOwnPropertyDescriptor(navigator, 'sendBeacon');

    vi.stubGlobal('fetch', fetchSpy);
    vi.stubGlobal('XMLHttpRequest', xhrSpy);
    vi.stubGlobal('WebSocket', webSocketSpy);
    vi.stubGlobal('open', openSpy);
    vi.stubGlobal('gtag', gtagSpy);
    vi.stubGlobal('dataLayer', { push: dataLayerPushSpy });
    vi.stubGlobal('indexedDB', {
      open: indexedDbOpenSpy,
      deleteDatabase: indexedDbDeleteSpy,
    });
    Object.defineProperty(navigator, 'sendBeacon', {
      configurable: true,
      value: beaconSpy,
    });

    try {
      render(<FitChefValueDemo />);
      await user.click(screen.getByRole('radio', { name: /Today/ }));
      await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
      await user.click(screen.getByRole('radio', { name: /This week/ }));
      await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
      await user.click(screen.getByRole('button', { name: 'Not now' }));

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(xhrSpy).not.toHaveBeenCalled();
      expect(webSocketSpy).not.toHaveBeenCalled();
      expect(beaconSpy).not.toHaveBeenCalled();
      expect(openSpy).not.toHaveBeenCalled();
      expect(gtagSpy).not.toHaveBeenCalled();
      expect(dataLayerPushSpy).not.toHaveBeenCalled();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
      expect(pushStateSpy).not.toHaveBeenCalled();
      expect(replaceStateSpy).not.toHaveBeenCalled();
      expect(indexedDbOpenSpy).not.toHaveBeenCalled();
      expect(indexedDbDeleteSpy).not.toHaveBeenCalled();
      expect(storageGetSpy).not.toHaveBeenCalled();
      expect(storageSetSpy).not.toHaveBeenCalled();
      expect(storageRemoveSpy).not.toHaveBeenCalled();
      expect(storageClearSpy).not.toHaveBeenCalled();
      expect(document.cookie).toBe(cookieBefore);
      expect(window.location.href).toBe(locationBefore);
    } finally {
      if (beaconDescriptor) {
        Object.defineProperty(navigator, 'sendBeacon', beaconDescriptor);
      } else {
        Reflect.deleteProperty(navigator, 'sendBeacon');
      }
    }
  });

  it('passes targeted accessibility checks in idle', async () => {
    const { container } = render(<FitChefValueDemo />);

    expect(await axe(container)).toHaveNoViolations();
  });

  it('passes targeted accessibility checks after Today is revealed', async () => {
    const user = userEvent.setup();
    const { container } = render(<FitChefValueDemo />);

    await user.click(screen.getByRole('radio', { name: /Today/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(screen.getByRole('heading', { name: 'Daily Plate' })).toBeVisible();

    expect(await axe(container)).toHaveNoViolations();
  });

  it('passes targeted accessibility checks after This week is revealed', async () => {
    const user = userEvent.setup();
    const { container } = render(<FitChefValueDemo />);

    await user.click(screen.getByRole('radio', { name: /This week/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(screen.getByRole('heading', { name: 'Weekly Planning' })).toBeVisible();

    expect(await axe(container)).toHaveNoViolations();
  });

  it('keeps imports and runtime constructs inside the static preview boundary', () => {
    const source = readFileSync(componentPath, 'utf8');
    const dependencies = enumerateModuleDependencies(source);

    expect(dependencies).toEqual(allowedDemoDependencies);
    expect(dependencies.join('\n')).not.toMatch(forbiddenDependencyFamilyPattern);
    expect(dependencyBoundaryViolations(source)).toEqual([]);
    expect(source).not.toMatch(
      /\b(useEffect|fetch|XMLHttpRequest|WebSocket|sendBeacon|localStorage|sessionStorage|indexedDB|setTimeout|setInterval|Promise)\b/,
    );
    expect(source).not.toMatch(/\b(gtag|dataLayer|PaymentRequest|cookieStore)\b|document\.cookie/);
    expect(source).not.toMatch(/\b(location|history)\b/);
  });

  it('uses the TypeScript parser for every supported module dependency carrier', () => {
    const parserFixture = `
      import defaultExport from 'default-import';
      import { named } from 'named-import';
      import 'bare-import';
      export { value } from 're-export';
      const commonJs = require('commonjs-require');
      const dynamic = import('dynamic-import');
    `;

    expect(enumerateModuleDependencies(parserFixture)).toEqual(
      [
        'default-import',
        'named-import',
        'bare-import',
        're-export',
        'commonjs-require',
        'dynamic-import',
      ].sort(),
    );
  });

  it('rejects forbidden dependency families, dynamic imports, and Vite meta-import carriers', () => {
    const negativeFixtures = [
      {
        name: 'bare analytics import',
        source: `import 'analytics/sink';`,
        expected: ['forbidden-family:analytics/sink'],
      },
      {
        name: 'CommonJS auth require',
        source: `const auth = require('../auth/session');`,
        expected: ['commonjs-require-call', 'forbidden-family:../auth/session'],
      },
      {
        name: 'CommonJS storage require',
        source: `const storage = require('../storage/cache');`,
        expected: ['commonjs-require-call', 'forbidden-family:../storage/cache'],
      },
      {
        name: 'CommonJS payment require',
        source: `const payment = require('../payment/client');`,
        expected: ['commonjs-require-call', 'forbidden-family:../payment/client'],
      },
      {
        name: 'literal dynamic import',
        source: `void import('./comparison-candidate');`,
        expected: ['dependency-not-allowed:./comparison-candidate', 'dynamic-import-call'],
      },
      {
        name: 'variable dynamic import',
        source: `const path = './comparison-candidate'; void import(path);`,
        expected: ['dynamic-import-call'],
      },
      {
        name: 'template dynamic import',
        source: `const variant = 'candidate'; void import(\`./\${variant}.tsx\`);`,
        expected: ['dynamic-import-call'],
      },
      {
        name: 'variable CommonJS require',
        source: `const path = '../auth/session'; const auth = require(path);`,
        expected: ['commonjs-require-call'],
      },
      {
        name: 'computed CommonJS require',
        source: `const family = 'auth'; const auth = require('../' + family + '/client');`,
        expected: ['commonjs-require-call', 'dependency-not-allowed:../'],
      },
      {
        name: 'Vite glob carrier',
        source: `const variants = import.meta.glob('./variants/*.tsx');`,
        expected: ['vite-meta-import'],
      },
      {
        name: 'Vite eager glob carrier',
        source: `const variants = import.meta.globEager('./variants/*.tsx');`,
        expected: ['vite-meta-import'],
      },
    ];

    negativeFixtures.forEach(({ name, source, expected }) => {
      expect(dependencyBoundaryViolations(source), name).toEqual(expected);
    });
  });

  it('keeps comparison candidates out of the complete finite marketing and Storybook census', () => {
    const marketingRuntimeGraph = marketingRuntimeSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const storybookGraph = storybookSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const completeCensusGraph = h2CensusSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const comparisonTogglePattern =
      /(?:fitchef|marketing)[^\n]{0,120}(?:candidate[_-]?y|guided[_-]?reveal|variant[_-]?h2)|(?:candidate[_-]?y|guided[_-]?reveal|variant[_-]?h2)[^\n]{0,120}(?:fitchef|marketing)/i;

    expect(marketingProductionModulePaths).toContain(componentPath);
    expect(marketingRuntimeSourcePaths).toEqual(
      expect.arrayContaining([
        componentPath,
        marketingStylesPath,
        marketingTokensPath,
        marketingPagePath,
        routesPath,
      ]),
    );
    expect(storybookSourcePaths.length).toBeGreaterThan(2);
    expect(readFileSync(storybookMainPath, 'utf8')).toContain("'../src/**/*.mdx'");
    expect(storybookSourcePaths).toEqual(
      expect.arrayContaining([hppTokenGuidelinesPath, designSystemGuidelinesPath]),
    );
    expect(completeCensusGraph).not.toMatch(
      /Candidate Y|Guided Reveal|FitChefValueDemoH2|Staged Review|FitChefValueDemoH3|Candidate Z/i,
    );
    expect(completeCensusGraph).not.toMatch(comparisonTogglePattern);
    expect(marketingRuntimeGraph).not.toContain('fitchef-onboarding-welcome-v1.png');
    expect(marketingRuntimeGraph).not.toMatch(/searchParams|URLSearchParams/);
    expect(storybookGraph).not.toMatch(comparisonTogglePattern);
  });

  it('keeps both marketing stylesheets inside the finite local CSS boundary', () => {
    [marketingStylesPath, marketingTokensPath].forEach((path) => {
      expect(cssBoundaryViolations(readFileSync(path, 'utf8')), path).toEqual([]);
    });

    const negativeFixtures = [
      {
        name: 'quoted comment delimiters cannot hide an import at-rule',
        source: `@charset "/*"; @import "https://cdn.example/remote.css"; :root { --note: "*/"; }`,
        expected: ['css-import'],
      },
      {
        name: 'quoted comment delimiters cannot hide remote URL or comparison content',
        source: `@charset "/*"; .hero { --note: "*/"; background-image: url("https://cdn.example/hero.png"); content: "Candidate Y"; }`,
        expected: ['comparison-content', 'remote-url'],
      },
      {
        name: 'invalid CSS fails closed',
        source: `.broken { color: red;`,
        expected: ['css-parse-error'],
      },
      {
        name: 'escaped import at-rule',
        source: String.raw`@im\70ort "https://cdn.example/remote.css";`,
        expected: ['css-escape-not-allowed'],
      },
      {
        name: 'escaped content property',
        source: String.raw`.variant::before { c\6fntent: "Candidate Y"; }`,
        expected: ['css-escape-not-allowed'],
      },
      {
        name: 'escaped URL function',
        source: String.raw`.hero { background-image: u\72l("https://cdn.example/hero.png"); }`,
        expected: ['css-escape-not-allowed', 'remote-url'],
      },
      {
        name: 'remote HTTPS import',
        source: `@import "https://cdn.example/remote.css";`,
        expected: ['css-import'],
      },
      {
        name: 'protocol-relative import',
        source: `@import url("//cdn.example/remote.css");`,
        expected: ['css-import'],
      },
      {
        name: 'local import',
        source: `@import "./local-marketing.css";`,
        expected: ['css-import'],
      },
      {
        name: 'remote HTTP asset URL',
        source: `.hero { background-image: url(http://cdn.example/hero.png); }`,
        expected: ['remote-url'],
      },
      {
        name: 'remote HTTPS asset URL',
        source: `.hero { background-image: url("https://cdn.example/hero.png"); }`,
        expected: ['remote-url'],
      },
      {
        name: 'protocol-relative asset URL',
        source: `.hero { background-image: url('//cdn.example/hero.png'); }`,
        expected: ['remote-url'],
      },
      {
        name: 'quoted HTTPS image-set address',
        source: `.hero { background-image: image-set("https://css-boundary.invalid/image-set.png" 1x); }`,
        expected: ['remote-url'],
      },
      {
        name: 'protocol-relative image-set address',
        source: `.hero { background-image: image-set("//css-boundary.invalid/image-set.png" 1x); }`,
        expected: ['remote-url'],
      },
      {
        name: 'Candidate Y generated content',
        source: `.variant::before { content: "Candidate Y"; }`,
        expected: ['comparison-content'],
      },
      {
        name: 'Guided Reveal generated content',
        source: `.variant::before { content: "Guided Reveal"; }`,
        expected: ['comparison-content'],
      },
      {
        name: 'H2 generated content',
        source: `.variant::before { content: "H2 comparison"; }`,
        expected: ['comparison-content'],
      },
    ];

    negativeFixtures.forEach(({ name, source, expected }) => {
      expect(cssBoundaryViolations(source), name).toEqual(expected);
    });

    const allowedFixtures = [
      {
        name: 'relative quoted image-set address',
        source: `.hero { background-image: image-set("../assets/local-hero.png" 1x); }`,
      },
      {
        name: 'root-local asset URL',
        source: `.hero { background-image: url('/assets/local-hero.png'); }`,
      },
      {
        name: 'ordinary harmless content',
        source: `.hero::before { content: "Ready"; }`,
      },
      {
        name: 'https word without address delimiter',
        source: `.note::before { content: "https"; }`,
      },
      {
        name: 'inert remote address comment',
        source: `/* background-image: url("https://commented.example/ignored.png"); */`,
      },
      {
        name: 'existing local URL and inert import content',
        source: `
          .hero { background-image: url('../assets/local-hero.png'); }
          .hero::before { content: "Ready"; }
          .note::before { content: "@import is inert text"; }
        `,
      },
    ];

    allowedFixtures.forEach(({ name, source }) => {
      expect(cssBoundaryViolations(source), name).toEqual([]);
    });
  });

  it('declares focus, reduced-motion, touch-target, and narrow-layout safeguards', () => {
    const styles = readFileSync(marketingStylesPath, 'utf8');

    expect(styles).toMatch(/\.ppm-fitchef-option:has\(input:focus-visible\)/);
    expect(styles).toMatch(/\.ppm-fitchef-option input:focus-visible/);
    expect(styles).toMatch(/min-height:\s*var\(--spacing-touch-large\)/);
    expect(styles).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    expect(styles).toMatch(/overflow-wrap:\s*anywhere/);
    expect(styles).toMatch(/@media \(max-width: 768px\)/);
    expect(styles).toMatch(
      /\.ppm-page \.ppm-btn--primary\s*\{[^}]*background:\s*var\(--color-blue-600\)/s,
    );
    expect(styles).toMatch(
      /\.ppm-page \.ppm-fitchef-confirm\s*\{[^}]*background:\s*var\(--color-blue-600\)/s,
    );
    expect(styles).toMatch(
      /\.ppm-page \.ppm-fitchef-secondary\s*\{[^}]*background:\s*rgba\(255, 255, 255, 0\.05\)/s,
    );
    expect(styles).toMatch(/\.ppm-step-grid\s*\{[^}]*repeat\(4, minmax\(0, 1fr\)\)/s);
    expect(styles).toMatch(/\.ppm-step-card\s*\{[^}]*height:\s*100%/s);
    expect(styles).not.toContain('color: var(--ppm-slate-500)');
  });

  it('keeps the finite retired-phrase list out of the complete production marketing census', () => {
    const completeMarketingCopy = marketingRuntimeSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const normalizedCompleteMarketingCopy = completeMarketingCopy
      .toLowerCase()
      .replaceAll('’', "'");
    const finiteRetiredGenericPhrases = [
      'at your own pace',
      'what feels useful',
      'starting point',
      "what we're building",
      'friendly look',
      'choose at your pace',
      'clear words about',
      'product-area correspondence',
    ];

    finiteRetiredGenericPhrases.forEach((phrase) => {
      expect(normalizedCompleteMarketingCopy).not.toContain(phrase);
    });
    expect(completeMarketingCopy).not.toMatch(
      /product direction|availability claim|unverified Store link/i,
    );
  });
});

describe('PulsePlateMarketingPage', (): void => {
  it('mounts one shared FitChef demo under one document heading', () => {
    renderMarketingPage();

    expect(screen.getByTestId('marketing-page')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Check your BMI and see how FitChef works',
      }),
    ).toBeVisible();
    expect(screen.getAllByTestId('fitchef-value-demo')).toHaveLength(1);
  });

  it('binds exact concrete copy to the intended semantic elements and multiplicity', () => {
    const { container } = renderMarketingPage();
    const requiredElement = (selector: string): HTMLElement => {
      const element = container.querySelector(selector);

      if (!(element instanceof HTMLElement)) {
        throw new Error(`Marketing element not found: ${selector}`);
      }

      return element;
    };
    const exactText = (element: Element | null, context: string): string => {
      if (!element) {
        throw new Error(`Marketing copy element not found: ${context}`);
      }

      return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
    };
    const exactTexts = (root: ParentNode, selector: string): string[] =>
      Array.from(root.querySelectorAll(selector), (element) => exactText(element, selector));

    const hero = requiredElement('#top');
    expect(exactText(hero.querySelector('.ppm-hero-copy > .ppm-eyebrow'), 'hero eyebrow')).toBe(
      'Free on the web',
    );
    expect(exactText(within(hero).getByRole('heading', { level: 1 }), 'hero h1')).toBe(
      'Check your BMI and see how FitChef works',
    );
    expect(exactText(hero.querySelector('.ppm-hero-body'), 'hero body')).toBe(
      'Use the free BMI calculator, or choose Today or This week in the FitChef preview to see whether it points to Daily Plate or Weekly Planning.',
    );
    expect(exactTexts(hero, '.ppm-actions .ppm-btn')).toEqual([
      'See how FitChef works',
      'Try the free BMI calculator',
    ]);
    expect(exactTexts(hero, '.ppm-pill-row > .ppm-pill')).toEqual([
      'Free website',
      'No purchases here',
      'Prepared FitChef preview',
    ]);
    expect(exactTexts(hero, '.ppm-action-card .ppm-action-text')).toEqual([
      'Daily Plate',
      'Free BMI calculator',
      'FitChef choice',
      'Weekly Planning',
    ]);
    expect(exactTexts(hero, '.ppm-action-card .ppm-action-helper')).toEqual([
      'For today',
      'On this website',
      'Today or this week',
      'For seven days',
    ]);
    expect(exactTexts(hero, '.ppm-stat-card .ppm-stat-label')).toEqual([
      'Website',
      'FitChef',
      'Today',
      'This week',
    ]);
    expect(exactTexts(hero, '.ppm-stat-card .ppm-stat-value')).toEqual([
      'Free BMI calculator',
      'Today or this week',
      'Daily Plate',
      'Weekly Planning',
    ]);
    expect(exactText(hero.querySelector('.ppm-fitchef-copy'), 'hero FitChef description')).toBe(
      'A short preview of how FitChef connects a choice to a planning view.',
    );
    expect(exactTexts(hero, '.ppm-preview > .ppm-preview-row > .ppm-pill')).toEqual([
      'Prepared example',
      'Nothing is saved',
    ]);
    expect(
      exactText(
        hero.querySelector('.ppm-subsection > .ppm-preview-row .ppm-subsection-title'),
        'hero choice subsection title',
      ),
    ).toBe('Try the two choices');
    expect(
      exactText(
        hero.querySelector('.ppm-subsection > .ppm-preview-row .ppm-subsection-meta'),
        'hero choice subsection meta',
      ),
    ).toBe('Today or this week');
    expect(
      exactText(hero.querySelector('.ppm-insight-card .ppm-subsection-title'), 'hero result title'),
    ).toBe('FitChef result');
    expect(exactText(hero.querySelector('.ppm-insight-card .ppm-pill'), 'hero result badge')).toBe(
      'Prepared example',
    );
    expect(
      exactText(hero.querySelector('.ppm-insight-card .ppm-insight-body'), 'hero result body'),
    ).toBe('Today points to Daily Plate. This week points to Weekly Planning.');
    expect(
      exactText(hero.querySelector('.ppm-insight-card .ppm-insight-note'), 'hero result note'),
    ).toBe('This preview uses no personal data.');

    const statusCards = requiredElement('.ppm-status-grid').querySelectorAll('.ppm-band-card');
    expect(
      Array.from(statusCards, (card) => ({
        title: exactText(card.querySelector('.ppm-band-card-title'), 'status title'),
        label: exactText(card.querySelector('.ppm-supporting'), 'status label'),
        body: exactText(card.querySelector('.ppm-band-card-copy'), 'status body'),
      })),
    ).toEqual([
      {
        title: 'Use the BMI calculator',
        label: 'Free website',
        body: 'Check BMI with the free tool on this website.',
      },
      {
        title: 'Choose Today or This week',
        label: 'FitChef preview',
        body: 'Both choices stay visible until you confirm.',
      },
      {
        title: 'PulsePlate for Apple devices',
        label: 'Apple devices',
        body: 'Read about the broader FitChef experience planned beyond the free website.',
      },
    ]);

    const how = requiredElement('#how-it-works');
    expect(exactText(within(how).getByRole('heading', { level: 2 }), 'how h2')).toBe(
      'Use the calculator, then try FitChef',
    );
    expect(exactText(how.querySelector('.ppm-header > .ppm-description'), 'how description')).toBe(
      'Check BMI, choose Today or This week, and see the result in the same card.',
    );
    expect(
      Array.from(how.querySelectorAll('.ppm-step-card'), (card) => ({
        number: exactText(card.querySelector('.ppm-step-number'), 'step number'),
        title: exactText(card.querySelector('.ppm-step-title'), 'step title'),
        body: exactText(card.querySelector('.ppm-step-copy'), 'step body'),
      })),
    ).toEqual([
      {
        number: '01',
        title: 'Open the free BMI calculator',
        body: 'View your BMI result on the website.',
      },
      {
        number: '02',
        title: 'Choose Today or This week',
        body: 'Both choices stay visible in the FitChef preview.',
      },
      {
        number: '03',
        title: 'See the result',
        body: 'The confirmed result stays in the preview card.',
      },
      {
        number: '04',
        title: 'Read about PulsePlate for Apple devices',
        body: 'Learn where the more advanced FitChef experience is planned.',
      },
    ]);

    const core = requiredElement('#core-surfaces');
    expect(exactText(within(core).getByRole('heading', { level: 2 }), 'core h2')).toBe(
      'Daily Plate and Weekly Planning',
    );
    expect(
      exactText(core.querySelector('.ppm-header > .ppm-description'), 'core description'),
    ).toBe('These are the two planning areas named by the FitChef preview.');
    expect(
      Array.from(core.querySelectorAll('.ppm-surface-card'), (card) => ({
        title: exactText(card.querySelector('.ppm-surface-title'), 'surface title'),
        label: exactText(card.querySelector('.ppm-pill'), 'surface label'),
        body: exactText(card.querySelector('.ppm-surface-copy'), 'surface body'),
      })),
    ).toEqual([
      {
        title: 'Free BMI calculator',
        label: 'Free web tool',
        body: 'Use the calculator on this website.',
      },
      {
        title: 'FitChef preview',
        label: 'Prepared example',
        body: 'Choose Today or This week, then confirm.',
      },
      {
        title: 'Daily Plate',
        label: 'Today',
        body: 'A day-focused area for planning meals.',
      },
      {
        title: 'Weekly Planning',
        label: 'This week',
        body: 'A seven-day area for looking ahead.',
      },
      {
        title: 'PulsePlate for Apple devices',
        label: 'Apple devices',
        body: 'A broader daily and weekly experience is being designed beyond this free website.',
      },
    ]);

    const trust = requiredElement('#trust-scope');
    expect(
      exactText(trust.querySelector('.ppm-header > .ppm-description'), 'trust description'),
    ).toBe(
      'Learn what the free website offers, how the FitChef preview works, and what is planned for Apple devices.',
    );
    expect(
      Array.from(trust.querySelectorAll('.ppm-trust-grid .ppm-trust-card'), (card) => ({
        title: exactText(card.querySelector('.ppm-trust-title'), 'trust card title'),
        body: exactText(card.querySelector('.ppm-trust-copy'), 'trust card body'),
      })),
    ).toEqual([
      {
        title: 'For everyday planning, not medical advice',
        body: 'PulsePlate supports everyday wellness planning. It does not diagnose, treat, or replace professional care.',
      },
      {
        title: 'The prepared preview uses no personal data',
        body: 'Your choice stays in this card. The example does not save it, open another area, or change a plan.',
      },
      {
        title: 'The website does not run FitChef AI',
        body: 'The result is prepared in advance. Today points to Daily Plate, and This week points to Weekly Planning.',
      },
    ]);
    expect(
      Array.from(trust.querySelectorAll('.ppm-faq-item'), (item) => ({
        question: exactText(item.querySelector('.ppm-faq-title'), 'trust FAQ question'),
        answer: exactText(item.querySelector('.ppm-faq-copy'), 'trust FAQ answer'),
      })),
    ).toEqual([
      {
        question: 'What can I use on this website?',
        answer:
          'You can use the free BMI calculator and try the prepared FitChef preview without a purchase step.',
      },
      {
        question: 'Does the FitChef preview run AI?',
        answer: 'No. It uses one fixed result for each of the two choices.',
      },
      {
        question: 'Where are more advanced FitChef ideas planned?',
        answer:
          'PulsePlate is being designed for Apple devices. This page does not claim current App Store availability.',
      },
    ]);

    const finalCta = requiredElement('#final-cta');
    expect(exactText(within(finalCta).getByRole('heading', { level: 2 }), 'final CTA h2')).toBe(
      'Try the BMI calculator or FitChef preview',
    );
    expect(exactText(finalCta.querySelector('.ppm-description'), 'final CTA body')).toBe(
      'Both are free to use on this website.',
    );
    expect(exactTexts(finalCta, '.ppm-cta-actions .ppm-btn')).toEqual([
      'Try free BMI',
      'Return to the FitChef preview',
    ]);

    const footer = requiredElement('footer');
    expect(
      exactText(footer.querySelector('.ppm-footer-copy > .ppm-description'), 'footer body'),
    ).toBe('Use the free BMI calculator or choose Today or This week in the FitChef preview.');
    expect(exactText(footer.querySelector('.ppm-footer-note'), 'footer wellness line')).toBe(
      'Everyday wellness planning — not medical advice.',
    );
  });

  it('allows only the exact current free-route and in-page acquisition destinations', () => {
    const { container } = renderMarketingPage();
    const allowedHrefs = new Set<string>([
      '/bmi',
      '#fitchef-demo',
      '#trust-scope',
      '#how-it-works',
      '#tiers',
      '#top',
    ]);
    const hrefs = Array.from(container.querySelectorAll<HTMLAnchorElement>('a[href]'))
      .map((link) => link.getAttribute('href'))
      .filter((href): href is string => href !== null);

    expect(screen.getByRole('link', { name: 'See how FitChef works' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );
    const freeBmiLinks = screen.getAllByRole('link', { name: 'Try the free BMI calculator' });
    expect(freeBmiLinks).toHaveLength(2);
    freeBmiLinks.forEach((link) => expect(link).toHaveAttribute('href', '/bmi'));
    expect(screen.getByRole('link', { name: 'Try free BMI' })).toHaveAttribute('href', '/bmi');
    expect(screen.getByRole('link', { name: 'Return to the FitChef preview' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );
    expect(Array.from(new Set(hrefs)).sort()).toEqual(Array.from(allowedHrefs).sort());
    hrefs.forEach((href) => expect(allowedHrefs.has(href)).toBe(true));
    hrefs
      .filter((href) => href.startsWith('#'))
      .forEach((href) => expect(container.querySelector(href)).toBeInstanceOf(HTMLElement));
    ['/app', '/pro', '/enter-key', '/welcome-gate-v1'].forEach((forbiddenHref) => {
      expect(hrefs).not.toContain(forbiddenHref);
    });
    within(container)
      .queryAllByRole('button')
      .forEach((button) =>
        expect(button).not.toHaveTextContent(
          /buy|subscribe|upgrade|trial|restore|download|payment/i,
        ),
      );
    within(container)
      .queryAllByRole('link')
      .forEach((link) =>
        expect(link).not.toHaveTextContent(/buy|subscribe|upgrade|trial|restore|download|payment/i),
      );
  });

  it('keeps the free-Web and prepared-example boundary explicit without internal language', () => {
    const { container } = renderMarketingPage();
    const visibleCopy = container.textContent ?? '';
    const demo = container.querySelector<HTMLElement>('#fitchef-demo');
    const trust = container.querySelector<HTMLElement>('#trust-scope');

    if (!demo || !trust) {
      throw new Error('Marketing FitChef or TrustScope section not found');
    }

    expect(visibleCopy).toContain('This website is free to use. Purchases are not offered here.');
    expect(demo).not.toHaveTextContent(
      'For now, you’re only choosing where to start. Nothing will open, be saved, or change.',
    );
    expect(demo).not.toHaveTextContent('For everyday planning — not medical advice.');
    expect(demo).not.toHaveTextContent(
      'This is a prepared website example. It does not run AI, use personal data, open anything, or change a plan.',
    );
    expect(trust).toHaveTextContent(
      'PulsePlate supports everyday wellness planning. It does not diagnose, treat, or replace professional care.',
    );
    expect(trust).toHaveTextContent(
      'The result is prepared in advance. Today points to Daily Plate, and This week points to Weekly Planning.',
    );
    expect(visibleCopy).not.toMatch(
      /\b(structure|structuring|daily_structure|weekly_structure|target_surface|authority|pipeline|best|personalized|generated for you|Pro)\b/i,
    );
    expect(visibleCopy).not.toMatch(
      /available now|live now|browser upgrade|AI[- ]powered|AI coaching/i,
    );
    expect(
      container.querySelector('a[href^="https://apps.apple.com"], a[href^="itms-apps:"]'),
    ).toBeNull();
    expect(visibleCopy).not.toMatch(/\$\d|price|trial|eligibility/i);
  });
});
