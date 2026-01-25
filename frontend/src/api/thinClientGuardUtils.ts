/**
 * Thin Client Guard Utilities
 *
 * RU: Вспомогательные функции для guard-тестов тонкого клиента.
 * EN: Helper functions for thin client guard tests.
 *
 * These utilities are extracted for testability - they handle
 * comment detection and inline comment stripping for pattern matching.
 *
 * @see thin-client-guards.test.ts (main guard tests)
 * @see docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md
 */

export type CommentState = {
  skip: boolean;
  newBlockCommentState: boolean;
};

/**
 * Strip inline comments from a line for pattern matching (quote-aware).
 *
 * RU: Обрезает inline-комментарии (//, /*) только если они НЕ внутри строковых литералов.
 * EN: Strips inline comments only when outside of string literals.
 *
 * Goal: reduce false positives from trailing comments WITHOUT creating false negatives.
 * This is a minimal scanner, not a full JS parser - we intentionally don't handle:
 * - Template literal interpolation ${...}
 * - Regex literals /pattern/
 * - Complex escape sequences beyond basic \\
 *
 * The trade-off is acceptable for guard tests that scan for obvious BMI logic violations.
 */
export function stripInlineComments(line: string): string {
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    const next = i + 1 < line.length ? line[i + 1] : '';

    if (escaped) {
      escaped = false;
      continue;
    }

    if (ch === '\\') {
      // escape only matters inside strings
      if (inSingle || inDouble || inBacktick) {
        escaped = true;
      }
      continue;
    }

    // Toggle quote states (only when not inside another quote type)
    if (!inDouble && !inBacktick && ch === "'") {
      inSingle = !inSingle;
      continue;
    }
    if (!inSingle && !inBacktick && ch === '"') {
      inDouble = !inDouble;
      continue;
    }
    if (!inSingle && !inDouble && ch === '`') {
      inBacktick = !inBacktick;
      continue;
    }

    // Detect comment starts only when NOT in any string literal
    if (!inSingle && !inDouble && !inBacktick) {
      if (ch === '/' && next === '/') {
        return line.slice(0, i);
      }
      if (ch === '/' && next === '*') {
        return line.slice(0, i);
      }
    }
  }

  return line;
}

/**
 * Check if a line is inside a comment (handles block comments).
 *
 * RU: Определяет, пропускать ли строку как комментарий.
 * EN: Returns whether to skip a line due to comment context.
 *
 * Rules:
 * - If we're inside a block comment, skip until we see "*&#47;" (closing ends the state).
 * - A line starting a block comment "/*" is skipped (single-line or multi-line start).
 * - A line starting with "//" is skipped.
 * - A line starting with "*" is considered JSDoc continuation ONLY when inside block comment.
 *   This prevents skipping valid multiline math like `width * height`.
 */
export function isLineInComment(
  line: string,
  inBlockComment: boolean
): CommentState {
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
    // Still in block comment - skip any line including JSDoc "*" continuations
    return { skip: true, newBlockCommentState: true };
  }

  // Not in block comment - check for new block comment start
  // Check for block comment start anywhere in the line
  const blockStartIdx = trimmed.indexOf('/*');
  if (blockStartIdx !== -1) {
    // Check if block comment closes on same line
    if (trimmed.includes('*/')) {
      // Single-line block comment - don't skip if there's code before it
      return { skip: blockStartIdx === 0, newBlockCommentState: false };
    }
    // Block comment starts but doesn't close - set state, skip only if at start
    return { skip: blockStartIdx === 0, newBlockCommentState: true };
  }

  // Single-line comment
  if (trimmed.startsWith('//')) {
    return { skip: true, newBlockCommentState: false };
  }

  // IMPORTANT: Do NOT treat "*" as comment outside block comment.
  // This prevents skipping valid multiline math like:
  // width
  //   * height

  // Not a comment
  return { skip: false, newBlockCommentState: false };
}
