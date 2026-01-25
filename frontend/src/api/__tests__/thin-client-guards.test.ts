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
    pattern: /(?<!['"`/])\b25\.0?\b(?!['"`])(?!\d)/,
    description: 'BMI threshold 25 (overweight boundary)',
  },
  {
    name: 'bmi-threshold-30',
    pattern: /(?<!['"`/])\b30\.0?\b(?!['"`])(?!\d)/,
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

// Canonical path for the allowed fetch file
const ALLOWED_FETCH_FILE = path.join('api', 'client.ts');

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

/**
 * Check if a line is inside a comment (handles block comments)
 * FIX A: Proper block comment handling
 */
function isLineInComment(
  line: string,
  inBlockComment: boolean
): { skip: boolean; newBlockCommentState: boolean } {
  const trimmed = line.trim();

  // If we're in a block comment, check if it ends on this line
  if (inBlockComment) {
    if (trimmed.includes('*/')) {
      // Block comment ends on this line - check if there's code after
      const afterClose = trimmed.substring(trimmed.indexOf('*/') + 2).trim();
      // If there's no code after the close, skip this line
      // Otherwise, we need to process the code after
      if (!afterClose) {
        return { skip: true, newBlockCommentState: false };
      }
      // There's code after - don't skip, but block comment is closed
      return { skip: false, newBlockCommentState: false };
    }
    // Still in block comment
    return { skip: true, newBlockCommentState: true };
  }

  // Not in block comment - check for new block comment start
  if (trimmed.startsWith('/*')) {
    // Check if block comment closes on same line
    if (trimmed.includes('*/')) {
      // Single-line block comment - skip this line
      return { skip: true, newBlockCommentState: false };
    }
    // Block comment starts but doesn't close
    return { skip: true, newBlockCommentState: true };
  }

  // Single-line comment or JSDoc continuation
  if (trimmed.startsWith('//') || trimmed.startsWith('*')) {
    return { skip: true, newBlockCommentState: false };
  }

  // Not a comment
  return { skip: false, newBlockCommentState: false };
}

/**
 * Check if file is the canonical client.ts (allowed to use fetch)
 * FIX C: Stricter client.ts skip condition using exact path
 */
function isAllowedFetchFile(relativePath: string): boolean {
  // Normalize path separators for cross-platform compatibility
  const normalized = relativePath.replace(/\\/g, '/');
  return normalized === 'api/client.ts' || normalized.endsWith('/api/client.ts');
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

        for (const { name, pattern } of FORBIDDEN_PATTERNS) {
          if (pattern.test(line)) {
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

        if (fetchPattern.test(line)) {
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
});
