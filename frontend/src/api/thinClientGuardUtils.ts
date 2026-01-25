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
  let inBlockComment = false;

  const out: string[] = [];

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    const next = i + 1 < line.length ? line[i + 1] : '';

    // If we're inside a block comment, skip content until we find the close.
    if (inBlockComment) {
      if (ch === '*' && next === '/') {
        inBlockComment = false;
        i += 1; // skip '/'
      }
      continue;
    }

    if (escaped) {
      // Keep escaped character in output and clear escape state.
      out.push(ch);
      escaped = false;
      continue;
    }

    if (ch === '\\') {
      // escape only matters inside strings
      out.push(ch);
      if (inSingle || inDouble || inBacktick) {
        escaped = true;
      }
      continue;
    }

    // Toggle quote states (only when not inside another quote type)
    if (!inDouble && !inBacktick && ch === "'") {
      inSingle = !inSingle;
      out.push(ch);
      continue;
    }
    if (!inSingle && !inBacktick && ch === '"') {
      inDouble = !inDouble;
      out.push(ch);
      continue;
    }
    if (!inSingle && !inDouble && ch === '`') {
      inBacktick = !inBacktick;
      out.push(ch);
      continue;
    }

    // Detect comment starts only when NOT in any string literal
    if (!inSingle && !inDouble && !inBacktick) {
      if (ch === '/' && next === '/') {
        break; // rest of the line is a comment
      }
      if (ch === '/' && next === '*') {
        inBlockComment = true;
        i += 1; // skip '*'
        continue;
      }
    }

    out.push(ch);
  }

  return out.join('');
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
  // We use a small quote-aware scanner to decide whether the line contains any code outside
  // comments, and to update block-comment state.
  //
  // Key bug fixed: don't mix lastIndexOf('/*') state detection with indexOf('/*') skip decision.
  // Lines like `/* closed */ code /* unclosed` MUST NOT be skipped (code exists), but must set
  // newBlockCommentState=true (unclosed block at end).
  let inBlock = inBlockComment;
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  let hasCodeOutsideComments = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    const next = i + 1 < line.length ? line[i + 1] : '';

    // Inside block comment: scan until close.
    if (inBlock) {
      if (ch === '*' && next === '/') {
        inBlock = false;
        i += 1; // skip '/'
      }
      continue;
    }

    // Inside string literal (quote-aware)
    if (inSingle || inDouble || inBacktick) {
      if (escaped) {
        escaped = false;
        continue;
      }
      if (ch === '\\') {
        escaped = true;
        continue;
      }
      if (inSingle && ch === "'") {
        inSingle = false;
      } else if (inDouble && ch === '"') {
        inDouble = false;
      } else if (inBacktick && ch === '`') {
        inBacktick = false;
      }
      continue;
    }

    // Not in block comment & not in string: detect comment starts
    if (ch === '/' && next === '/') {
      break; // rest of line is a comment
    }
    if (ch === '/' && next === '*') {
      inBlock = true;
      i += 1; // skip '*'
      continue;
    }

    // Enter string literal (counts as code)
    if (ch === "'") {
      inSingle = true;
      hasCodeOutsideComments = true;
      continue;
    }
    if (ch === '"') {
      inDouble = true;
      hasCodeOutsideComments = true;
      continue;
    }
    if (ch === '`') {
      inBacktick = true;
      hasCodeOutsideComments = true;
      continue;
    }

    // Any non-whitespace char outside comments => this line has code.
    if (ch.trim() !== '') {
      hasCodeOutsideComments = true;
    }
  }

  return { skip: !hasCodeOutsideComments, newBlockCommentState: inBlock };
}
