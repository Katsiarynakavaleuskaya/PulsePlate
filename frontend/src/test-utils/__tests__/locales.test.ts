/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  MAX_ALLOWED_DUPLICATES,
  MAX_DISPLAY_LENGTH,
  STRING_LENGTH_LIMITS,
  collectKeyPaths,
  getMaxLength,
  checkLengths,
  TestLogger
} from '../locales';

describe('locales test utilities', () => {
  describe('constants', () => {
    it('should have correct constant values', () => {
      expect(MAX_ALLOWED_DUPLICATES).toBe(50);
      expect(MAX_DISPLAY_LENGTH).toBe(50);
      expect(STRING_LENGTH_LIMITS.default).toBe(500);
      expect(STRING_LENGTH_LIMITS.extended).toBe(1000);
    });
  });

  describe('collectKeyPaths', () => {
    it('should return empty array for null', () => {
      expect(collectKeyPaths(null)).toEqual([]);
    });

    it('should return empty array for non-object', () => {
      expect(collectKeyPaths('string')).toEqual([]);
      expect(collectKeyPaths(123)).toEqual([]);
      expect(collectKeyPaths(true)).toEqual([]);
    });

    it('should collect paths from simple object', () => {
      const obj = { a: 1, b: 2 };
      const paths = collectKeyPaths(obj);
      expect(paths).toContain('a');
      expect(paths).toContain('b');
    });

    it('should collect nested paths', () => {
      const obj = { a: { b: { c: 1 } } };
      const paths = collectKeyPaths(obj);
      expect(paths).toContain('a');
      expect(paths).toContain('a.b');
      expect(paths).toContain('a.b.c');
    });

    it('should handle arrays', () => {
      const obj = { items: [1, 2, 3] };
      const paths = collectKeyPaths(obj);
      expect(paths).toContain('items');
      expect(paths).toContain('items.0');
      expect(paths).toContain('items.1');
      expect(paths).toContain('items.2');
    });
  });

  describe('getMaxLength', () => {
    it('should return extended limit for legal paths', () => {
      expect(getMaxLength('legal')).toBe(STRING_LENGTH_LIMITS.extended);
      expect(getMaxLength('some.legal.text')).toBe(STRING_LENGTH_LIMITS.extended);
    });

    it('should return extended limit for description paths', () => {
      expect(getMaxLength('description')).toBe(STRING_LENGTH_LIMITS.extended);
      expect(getMaxLength('some.description.text')).toBe(STRING_LENGTH_LIMITS.extended);
    });

    it('should return extended limit for disclaimer paths', () => {
      expect(getMaxLength('disclaimer')).toBe(STRING_LENGTH_LIMITS.extended);
      expect(getMaxLength('some.disclaimer.text')).toBe(STRING_LENGTH_LIMITS.extended);
    });

    it('should return default limit for other paths', () => {
      expect(getMaxLength('title')).toBe(STRING_LENGTH_LIMITS.default);
      expect(getMaxLength('some.other.path')).toBe(STRING_LENGTH_LIMITS.default);
    });
  });

  describe('checkLengths', () => {
    it('should return empty array for valid string', () => {
      const issues = checkLengths('valid string');
      expect(issues).toEqual([]);
    });

    it('should return issue for empty string', () => {
      const issues = checkLengths('');
      expect(issues).toHaveLength(1);
      expect(issues[0]).toContain('Invalid length 0');
    });

    it('should return issue for string too long', () => {
      const longString = 'a'.repeat(STRING_LENGTH_LIMITS.default + 1);
      const issues = checkLengths(longString);
      expect(issues).toHaveLength(1);
      expect(issues[0]).toContain(`Invalid length ${longString.length}`);
    });

    it('should handle extended limit for special paths', () => {
      const longString = 'a'.repeat(STRING_LENGTH_LIMITS.extended + 1);
      const issues = checkLengths(longString, 'legal');
      expect(issues).toHaveLength(1);
      expect(issues[0]).toContain(`Invalid length ${longString.length}`);
    });

    it('should check nested objects', () => {
      const obj = {
        valid: 'short',
        invalid: 'a'.repeat(STRING_LENGTH_LIMITS.default + 1)
      };
      const issues = checkLengths(obj);
      expect(issues).toHaveLength(1);
      expect(issues[0]).toContain('invalid:');
    });

    it('should handle null values', () => {
      const issues = checkLengths(null);
      expect(issues).toEqual([]);
    });

    it('should truncate long strings in error messages', () => {
      const veryLongString = 'a'.repeat(STRING_LENGTH_LIMITS.default + 1);
      const issues = checkLengths(veryLongString);
      expect(issues).toHaveLength(1);
      expect(issues[0]).toContain('...');
    });
  });

  describe('TestLogger', () => {
    let logger: TestLogger;

    beforeEach(() => {
      logger = new TestLogger();
    });

    it('should store logs without console output in test environment', () => {
      logger.warn('test message');
      const logs = logger.getLogs();
      expect(logs).toHaveLength(1);
      expect(logs[0]).toBe('test message');
    });

    it('should handle multiple arguments', () => {
      logger.warn('test message', 'arg1', 'arg2');
      const logs = logger.getLogs();
      expect(logs[0]).toBe('test message arg1 arg2');
    });

    it('should serialize non-string arguments', () => {
      logger.warn('test message', { key: 'value' });
      const logs = logger.getLogs();
      expect(logs[0]).toBe('test message {"key":"value"}');
    });

    it('should clear logs', () => {
      logger.warn('test message');
      expect(logger.getLogs()).toHaveLength(1);

      logger.clear();
      expect(logger.getLogs()).toHaveLength(0);
    });

    it('should return copy of logs', () => {
      logger.warn('test message');
      const logs1 = logger.getLogs();
      const logs2 = logger.getLogs();

      expect(logs1).toEqual(logs2);
      expect(logs1).not.toBe(logs2); // Different arrays
    });
  });
});
