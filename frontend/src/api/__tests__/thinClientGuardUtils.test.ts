/**
 * Unit Tests for Thin Client Guard Utilities
 *
 * RU: Регрессионные тесты для вспомогательных функций guard-тестов.
 * EN: Regression tests for guard helper functions.
 *
 * These tests ensure the guard utilities correctly handle:
 * - Inline comment stripping
 * - Block/line comment detection
 * - Edge cases that caused false positives/negatives
 *
 * @see thinClientGuardUtils.ts
 * @see thin-client-guards.test.ts (main guard tests)
 */

import { describe, expect, it } from 'vitest';
import { isLineInComment, stripInlineComments } from '../thinClientGuardUtils';

describe('stripInlineComments()', () => {
  describe('basic comment stripping', () => {
    it('strips // inline comments', () => {
      const line = 'const x = 1; // bmi >= 25';
      expect(stripInlineComments(line)).toBe('const x = 1; ');
    });

    it('strips /* inline block comments', () => {
      const line = 'const y = 2; /* bmi >= 30 */';
      expect(stripInlineComments(line)).toBe('const y = 2; ');
    });

    it('returns empty for pure // comment line', () => {
      const line = '// bmi >= 25';
      expect(stripInlineComments(line).trim()).toBe('');
    });

    it('returns empty for pure /* comment line', () => {
      const line = '/* bmi >= 30 */';
      expect(stripInlineComments(line).trim()).toBe('');
    });

    it('preserves code before comment', () => {
      const line = 'const threshold = value; // threshold 25';
      const result = stripInlineComments(line);
      expect(result).toBe('const threshold = value; ');
      // Ensure the guard pattern would NOT match after stripping
      expect(result).not.toContain('25');
    });

    it('handles line with no comments', () => {
      const line = 'const bmi = response.bmi;';
      expect(stripInlineComments(line)).toBe('const bmi = response.bmi;');
    });
  });

  describe('quote-aware (prevents false negatives)', () => {
    it('does NOT cut at // inside double-quoted string (URL)', () => {
      // This was the bug: "http://..." would be cut at "//" causing false negatives
      const line = 'const url = "http://example.com"; const bmi = 25;';
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('const bmi = 25');
      expect(stripped).toBe(line); // No cutting should occur
    });

    it('does NOT cut at // inside single-quoted string', () => {
      const line = "const url = 'http://example.com'; const bmi = 25;";
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('const bmi = 25');
    });

    it('does NOT cut at // inside backtick string', () => {
      const line = 'const url = `http://example.com`; const bmi = 25;';
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('const bmi = 25');
    });

    it('does NOT cut at /* inside string literal', () => {
      const line = "const s = 'a/*b'; const bmi = 30;";
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('const bmi = 30');
    });

    it('removes /* ... */ but keeps code after */ (prevents guard blind spot)', () => {
      const line = 'const a = 1; /* bmi >= 25 */ const b = 25;';
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('const b = 25;');
      expect(stripped).not.toContain('bmi >= 25');
    });

    it('keeps URL strings and keeps code after */', () => {
      const line = 'const url = "http://x"; /* c */ const b = 25;';
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('"http://x"');
      expect(stripped).toContain('const b = 25;');
    });

    it('unterminated /* removes rest of line', () => {
      const line = 'const a = 1; /* unterminated bmi >= 25';
      const stripped = stripInlineComments(line);
      expect(stripped).toBe('const a = 1; ');
    });

    it('cuts at // outside strings after string ends', () => {
      const line = 'const url = "http://example.com"; // real comment with 25';
      const stripped = stripInlineComments(line);
      expect(stripped).toBe('const url = "http://example.com"; ');
      expect(stripped).not.toContain('25');
    });

    it('handles escaped quotes inside strings', () => {
      const line = 'const s = "say \\"hi\\""; const bmi = 25;';
      const stripped = stripInlineComments(line);
      expect(stripped).toContain('const bmi = 25');
    });

    it('handles mixed quote types correctly', () => {
      const line = `const s = "it's a test"; // comment`;
      const stripped = stripInlineComments(line);
      expect(stripped).toBe(`const s = "it's a test"; `);
    });
  });
});

describe('isLineInComment()', () => {
  describe('outside block comment (inBlockComment=false)', () => {
    it('does not skip "*" lines outside block comment (math expression)', () => {
      // This was the Cubic bug: `* height` was incorrectly skipped
      const res = isLineInComment('  * height', false);
      expect(res.skip).toBe(false);
      expect(res.newBlockCommentState).toBe(false);
    });

    it('does not skip multiplication expressions', () => {
      const res = isLineInComment('width * height', false);
      expect(res.skip).toBe(false);
    });

    it('skips // comment lines', () => {
      const res = isLineInComment('  // comment', false);
      expect(res.skip).toBe(true);
      expect(res.newBlockCommentState).toBe(false);
    });

    it('starts block comment on /* and sets state', () => {
      const res = isLineInComment('/* start of comment', false);
      expect(res.skip).toBe(true);
      expect(res.newBlockCommentState).toBe(true);
    });

    it('handles single-line block comment /* ... */', () => {
      const res = isLineInComment('/* single line */', false);
      expect(res.skip).toBe(true);
      expect(res.newBlockCommentState).toBe(false);
    });

    it('does not skip regular code', () => {
      const res = isLineInComment('const x = 5;', false);
      expect(res.skip).toBe(false);
      expect(res.newBlockCommentState).toBe(false);
    });
  });

  describe('inside block comment (inBlockComment=true)', () => {
    it('skips "*" lines inside block comment (JSDoc continuation)', () => {
      const res = isLineInComment('  * @param docs', true);
      expect(res.skip).toBe(true);
      expect(res.newBlockCommentState).toBe(true);
    });

    it('skips regular text inside block comment', () => {
      const res = isLineInComment('still in comment', true);
      expect(res.skip).toBe(true);
      expect(res.newBlockCommentState).toBe(true);
    });

    it('ends block comment on */ and clears state', () => {
      const res = isLineInComment('end of comment */', true);
      expect(res.skip).toBe(true);
      expect(res.newBlockCommentState).toBe(false);
    });

    it('handles code after block comment close', () => {
      const res = isLineInComment('*/ const x = 5;', true);
      // There's code after - don't skip so we can scan it
      expect(res.skip).toBe(false);
      expect(res.newBlockCommentState).toBe(false);
    });
  });

  describe('block comment lifecycle', () => {
    it('tracks state through multi-line block comment (no code after close)', () => {
      // Simulate scanning through a block comment that closes cleanly
      const lines = ['/* start', ' * middle', ' * still in', ' */'];

      let state = false;
      const results: boolean[] = [];

      for (const line of lines) {
        const res = isLineInComment(line, state);
        results.push(res.skip);
        state = res.newBlockCommentState;
      }

      // All lines should be skipped, final state should be false
      expect(results).toEqual([true, true, true, true]);
      expect(state).toBe(false);
    });

    it('does not skip line with code after block comment close', () => {
      // When there's code after */, we don't skip so we can scan that code
      const lines = ['/* start', '*/ const x = 25;'];

      let state = false;
      const results: boolean[] = [];

      for (const line of lines) {
        const res = isLineInComment(line, state);
        results.push(res.skip);
        state = res.newBlockCommentState;
      }

      // First line skipped (starts comment), second NOT skipped (has code after)
      expect(results).toEqual([true, false]);
      expect(state).toBe(false);
    });
  });
});

describe('FORBIDDEN_PATTERNS regex (threshold correctness)', () => {
  // These patterns are copied from thin-client-guards.test.ts to verify correctness
  const bmi25Pattern = /(?<!['"`/.])(?<!:\s)\b25(\.0{1,2})?\b(?!['"`])(?!\d)/;
  const bmi30Pattern = /(?<!['"`/.])(?<!:\s)\b30(\.0{1,2})?\b(?!['"`])(?!\d)/;

  describe('bmi-threshold-25', () => {
    it('matches "bmi >= 25"', () => {
      expect(bmi25Pattern.test('if (bmi >= 25)')).toBe(true);
    });

    it('matches "bmi >= 25.0"', () => {
      expect(bmi25Pattern.test('if (bmi >= 25.0)')).toBe(true);
    });

    it('matches "bmi >= 25.00"', () => {
      expect(bmi25Pattern.test('if (bmi >= 25.00)')).toBe(true);
    });

    it('does NOT match "250" (different number)', () => {
      expect(bmi25Pattern.test('if (count >= 250)')).toBe(false);
    });

    it('does NOT match "0.25" (decimal coefficient)', () => {
      expect(bmi25Pattern.test('const ratio = 0.25')).toBe(false);
    });

    it('does NOT match "percentage: 25" (key-value context)', () => {
      expect(bmi25Pattern.test('percentage: 25')).toBe(false);
    });

    it('does NOT match quoted "25"', () => {
      expect(bmi25Pattern.test('const s = "25"')).toBe(false);
    });
  });

  describe('bmi-threshold-30', () => {
    it('matches "bmi >= 30"', () => {
      expect(bmi30Pattern.test('if (bmi >= 30)')).toBe(true);
    });

    it('matches "bmi >= 30.0"', () => {
      expect(bmi30Pattern.test('if (bmi >= 30.0)')).toBe(true);
    });

    it('matches "bmi >= 30.00"', () => {
      expect(bmi30Pattern.test('if (bmi >= 30.00)')).toBe(true);
    });

    it('does NOT match "300" (different number)', () => {
      expect(bmi30Pattern.test('if (count >= 300)')).toBe(false);
    });

    it('does NOT match "age: 30" (key-value context)', () => {
      expect(bmi30Pattern.test('age: 30')).toBe(false);
    });

    it('does NOT match quoted "30"', () => {
      expect(bmi30Pattern.test('const s = "30"')).toBe(false);
    });
  });
});
