/**
 * Thin Client Guards Tests
 *
 * RU: Защитные тесты против появления BMI логики во frontend коде.
 * EN: Guard tests to prevent BMI logic from appearing in frontend code.
 *
 * These tests scan the frontend source code to detect violations of the
 * thin-client policy. The frontend should be a pure renderer of backend
 * contracts, with zero business logic.
 *
 * Forbidden patterns:
 * - BMI thresholds (18.5, 24.9, 25.0, 30.0)
 * - BMI comparisons (if bmi <, bmi >, etc.)
 * - Category/risk assignments
 * - Local BMI calculation functions
 * - Direct fetch() calls outside client.ts
 *
 * @see docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md
 * @see frontend/AGENTS.md (Thin HTTP Adapter Policy)
 */

import { describe, it, expect, beforeAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { isLineInComment, stripInlineComments } from '../thinClientGuardUtils';

// Directories to scan (relative to frontend/src)
const SCAN_DIRS = ['api', 'pages', 'components', 'features', 'hooks', 'lib'];

// Directories/files to exclude from scanning
const EXCLUDE_PATTERNS = [
  '__tests__',
  '.test.',
  '.spec.',
  'mock',
  'fixture',
  'schema.ts', // OpenAPI generated - contains threshold examples in comments
  'openapi.json', // OpenAPI spec
];

// Forbidden patterns that indicate BMI logic violations
const FORBIDDEN_PATTERNS: Array<{ name: string; pattern: RegExp; description: string }> = [
  {
    name: 'bmi-threshold-18.5',
    pattern: /(?<!['"`/])\b18\.5\b(?!['"`])/,
    description: 'BMI threshold 18.5 (underweight boundary)',
  },
  {
    name: 'bmi-threshold-24.9',
    pattern: /(?<!['"`/])\b24\.9\b(?!['"`])/,
    description: 'BMI threshold 24.9 (normal upper boundary)',
  },
  {
    name: 'bmi-threshold-25',
    // Match 25, 25.0, 25.00 but NOT 0.25 or percentage: 25
    // Cubic fix: dot optional, but avoid false positives
    // Lookbehind excludes: quotes, slash, dot, colon+space (age: 30)
    pattern: /(?<!['"`/.])(?<!:\s)\b25(\.0{1,2})?\b(?!['"`])(?!\d)/,
    description: 'BMI threshold 25 (overweight boundary)',
  },
  {
    name: 'bmi-threshold-30',
    // Match 30, 30.0, 30.00 but NOT age: 30
    // Cubic fix: dot optional, but avoid false positives
    pattern: /(?<!['"`/.])(?<!:\s)\b30(\.0{1,2})?\b(?!['"`])(?!\d)/,
    description: 'BMI threshold 30 (obesity boundary)',
  },
  {
    name: 'bmi-comparison',
    pattern: /\bbmi\s*[<>=!]+\s*\d/i,
    description: 'BMI value comparison (business logic)',
  },
  {
    name: 'category-assignment',
    pattern: /\bcategory\s*=\s*['"`]?(underweight|normal|overweight|obese)/i,
    description: 'BMI category assignment (business logic)',
  },
  {
    name: 'risk-assignment',
    pattern: /\brisk\s*=\s*['"`]?(low|moderate|high|extreme)/i,
    description: 'Risk level assignment (business logic)',
  },
  {
    name: 'local-bmi-calc',
    // Exclude API function calls (calculateBMI from api/bmi.ts is allowed)
    // Match only: function declarations with BMI math, or non-API calculateBMI usage
    pattern: /\b(computeBMI|getBMICategory|calcBMI)\s*\(/i,
    description: 'Local BMI calculation function (should use backend)',
  },
  {
    name: 'bmi-formula',
    // Match BMI formula: weight / (height * height) or similar
    pattern: /weight\s*\/\s*\(?\s*height\s*\*\s*height/i,
    description: 'BMI formula implementation (should use backend)',
  },
];

/**
 * Source file with content for scanning
 */
interface SourceFile {
  path: string;
  relativePath: string;
  content: string;
  lines: string[];
}

/**
 * Recursively get all TypeScript/TSX files in a directory
 */
function getSourceFilePaths(dir: string): string[] {
  const files: string[] = [];

  if (!fs.existsSync(dir)) {
    return files;
  }

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    // Skip excluded patterns
    if (EXCLUDE_PATTERNS.some((pattern) => fullPath.includes(pattern))) {
      continue;
    }

    if (entry.isDirectory()) {
      files.push(...getSourceFilePaths(fullPath));
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Load source files with content (shared helper to avoid duplicate FS reads)
 * FIX B: Shared helper for file collection
 */
function collectSourceFiles(srcDir: string, scanDirs: string[]): SourceFile[] {
  const sourceFiles: SourceFile[] = [];

  for (const subDir of scanDirs) {
    const dirPath = path.join(srcDir, subDir);
    const filePaths = getSourceFilePaths(dirPath);

    for (const filePath of filePaths) {
      const content = fs.readFileSync(filePath, 'utf-8');
      sourceFiles.push({
        path: filePath,
        relativePath: path.relative(srcDir, filePath),
        content,
        lines: content.split('\n'),
      });
    }
  }

  return sourceFiles;
}

// Helper functions (isLineInComment, stripInlineComments) are imported from thinClientGuardUtils.ts
// See thinClientGuardUtils.test.ts for unit tests on these helpers

/**
 * Check if file is the canonical client.ts (allowed to use fetch)
 * FIX C: Stricter client.ts skip condition using exact path
 */
function isAllowedFetchFile(relativePath: string): boolean {
  // Normalize path separators for cross-platform compatibility
  const normalized = relativePath.replace(/\\/g, '/');
  return normalized === 'api/client.ts' || normalized.endsWith('/api/client.ts');
}

function isAllowedWebSocketFile(relativePath: string): boolean {
  const normalized = relativePath.replace(/\\/g, '/');
  return normalized === 'api/wsClient.ts' || normalized.endsWith('/api/wsClient.ts');
}

describe('ThinClientGuards', () => {
  const srcDir = path.resolve(__dirname, '../..');

  // FIX B: Collect files once, share between tests
  let sourceFiles: SourceFile[];

  beforeAll(() => {
    sourceFiles = collectSourceFiles(srcDir, SCAN_DIRS);
  });

  it('should not contain BMI thresholds or business logic in frontend code', () => {
    const allViolations: Array<{
      file: string;
      pattern: string;
      line: number;
      content: string;
    }> = [];

    for (const file of sourceFiles) {
      let inBlockComment = false;

      for (let i = 0; i < file.lines.length; i++) {
        const line = file.lines[i];
        const lineNum = i + 1;

        // FIX A/D: Consistent comment handling with block comment support
        const commentCheck = isLineInComment(line, inBlockComment);
        inBlockComment = commentCheck.newBlockCommentState;

        if (commentCheck.skip) {
          continue;
        }

        // CodeRabbit fix: strip inline comments before pattern matching
        const candidate = stripInlineComments(line);
        if (!candidate.trim()) {
          continue;
        }

        for (const { name, pattern } of FORBIDDEN_PATTERNS) {
          if (pattern.test(candidate)) {
            allViolations.push({
              file: file.relativePath,
              pattern: name,
              line: lineNum,
              content: line.trim().substring(0, 100),
            });
          }
        }
      }
    }

    if (allViolations.length > 0) {
      const report = allViolations
        .map((v) => `  ${v.file}:${v.line} [${v.pattern}]\n    ${v.content}`)
        .join('\n');

      expect.fail(
        `Thin Client Policy Violation!\n\n` +
          `Found ${allViolations.length} violation(s) in frontend code:\n\n` +
          `${report}\n\n` +
          `The frontend must be a thin HTTP adapter with zero BMI logic.\n` +
          `All calculations and interpretations must come from the backend.\n\n` +
          `See: frontend/AGENTS.md (Thin HTTP Adapter Policy)`
      );
    }

    expect(allViolations).toHaveLength(0);
  });

  it('should use api() function for all HTTP calls (no direct fetch)', () => {
    const violations: Array<{ file: string; line: number; content: string }> = [];
    const fetchPattern = /\bfetch\s*\(/;

    for (const file of sourceFiles) {
      // FIX C: Use exact path check for client.ts
      if (isAllowedFetchFile(file.relativePath)) {
        continue;
      }

      let inBlockComment = false;

      for (let i = 0; i < file.lines.length; i++) {
        const line = file.lines[i];

        // FIX A/D: Consistent comment handling with block comment support
        const commentCheck = isLineInComment(line, inBlockComment);
        inBlockComment = commentCheck.newBlockCommentState;

        if (commentCheck.skip) {
          continue;
        }

        // CodeRabbit fix: strip inline comments before pattern matching
        const candidate = stripInlineComments(line);
        if (!candidate.trim()) {
          continue;
        }

        if (fetchPattern.test(candidate)) {
          violations.push({
            file: file.relativePath,
            line: i + 1,
            content: line.trim().substring(0, 100),
          });
        }
      }
    }

    if (violations.length > 0) {
      const report = violations
        .map((v) => `  ${v.file}:${v.line}\n    ${v.content}`)
        .join('\n');

      expect.fail(
        `Direct fetch() usage detected!\n\n` +
          `Found ${violations.length} violation(s):\n\n` +
          `${report}\n\n` +
          `All HTTP calls must go through api() from src/api/client.ts.\n` +
          `Direct fetch() calls violate the thin client policy.`
      );
    }

    expect(violations).toHaveLength(0);
  });

  it('should create WebSocket connections only in api/wsClient.ts', () => {
    const violations: Array<{ file: string; line: number; content: string }> = [];
    const websocketCtorPattern = /\bnew\s+WebSocket\s*\(/;

    for (const file of sourceFiles) {
      if (isAllowedWebSocketFile(file.relativePath)) {
        continue;
      }

      let inBlockComment = false;

      for (let i = 0; i < file.lines.length; i++) {
        const line = file.lines[i];
        const commentCheck = isLineInComment(line, inBlockComment);
        inBlockComment = commentCheck.newBlockCommentState;

        if (commentCheck.skip) {
          continue;
        }

        const candidate = stripInlineComments(line);
        if (!candidate.trim()) {
          continue;
        }

        if (websocketCtorPattern.test(candidate)) {
          violations.push({
            file: file.relativePath,
            line: i + 1,
            content: line.trim().substring(0, 100),
          });
        }
      }
    }

    if (violations.length > 0) {
      const report = violations
        .map((v) => `  ${v.file}:${v.line}\n    ${v.content}`)
        .join('\n');

      expect.fail(
        `Direct WebSocket usage detected!\n\n` +
          `Found ${violations.length} violation(s):\n\n` +
          `${report}\n\n` +
          `WebSocket connections must be created only in src/api/wsClient.ts.\n` +
          `Components/hooks should consume thin adapter abstractions only.`
      );
    }

    expect(violations).toHaveLength(0);
  });
});
