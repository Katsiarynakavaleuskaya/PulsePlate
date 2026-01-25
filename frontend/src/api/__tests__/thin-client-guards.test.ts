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
 *
 * @see docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md
 * @see frontend/AGENTS.md (Thin HTTP Adapter Policy)
 */

import { describe, it, expect } from 'vitest';
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

/**
 * Recursively get all TypeScript/TSX files in a directory
 */
function getSourceFiles(dir: string): string[] {
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
      files.push(...getSourceFiles(fullPath));
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Scan a file for forbidden patterns
 */
function scanFile(
  filePath: string
): Array<{ pattern: string; line: number; content: string }> {
  const violations: Array<{ pattern: string; line: number; content: string }> = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // Skip comments
    const trimmed = line.trim();
    if (trimmed.startsWith('//') || trimmed.startsWith('*') || trimmed.startsWith('/*')) {
      continue;
    }

    for (const { name, pattern } of FORBIDDEN_PATTERNS) {
      if (pattern.test(line)) {
        violations.push({
          pattern: name,
          line: lineNum,
          content: line.trim().substring(0, 100),
        });
      }
    }
  }

  return violations;
}

describe('ThinClientGuards', () => {
  const srcDir = path.resolve(__dirname, '../..');

  it('should not contain BMI thresholds or business logic in frontend code', () => {
    const allViolations: Array<{
      file: string;
      pattern: string;
      line: number;
      content: string;
    }> = [];

    for (const subDir of SCAN_DIRS) {
      const dirPath = path.join(srcDir, subDir);
      const files = getSourceFiles(dirPath);

      for (const file of files) {
        const violations = scanFile(file);
        for (const v of violations) {
          allViolations.push({
            file: path.relative(srcDir, file),
            ...v,
          });
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

    for (const subDir of SCAN_DIRS) {
      const dirPath = path.join(srcDir, subDir);
      const files = getSourceFiles(dirPath);

      for (const file of files) {
        // Skip the client.ts file (it's allowed to use fetch)
        if (file.includes('client.ts')) {
          continue;
        }

        const content = fs.readFileSync(file, 'utf-8');
        const lines = content.split('\n');

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          const trimmed = line.trim();

          // Skip comments
          if (trimmed.startsWith('//') || trimmed.startsWith('*')) {
            continue;
          }

          if (fetchPattern.test(line)) {
            violations.push({
              file: path.relative(srcDir, file),
              line: i + 1,
              content: trimmed.substring(0, 100),
            });
          }
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
