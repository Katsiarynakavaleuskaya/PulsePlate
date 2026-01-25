/**
 * Unit tests for normalizeApiUrl() helper
 *
 * RU: Тесты нормализации URL для избежания дублирования /api или /api/v1.
 * EN: Tests for URL normalization to avoid duplicate API path segments.
 *
 * This is a pure function test (no network, no MSW).
 */

import { describe, it, expect } from 'vitest';
import { normalizeApiUrl } from '../client';

describe('normalizeApiUrl', () => {
  describe('deduplication when base contains /api/v1', () => {
    it('should deduplicate /api/v1 when base and path both contain it', () => {
      const base = 'http://localhost:8000/api/v1';
      const path = '/api/v1/shoplist/export.csv';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/v1/shoplist/export.csv'
      );
    });

    it('should work with trailing slash in base', () => {
      const base = 'http://localhost:8000/api/v1/';
      const path = '/api/v1/export.pdf';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/v1/export.pdf'
      );
    });

    it('should handle nested paths correctly', () => {
      const base = 'http://localhost:8000/api/v1';
      const path = '/api/v1/pro/nutrition/targets';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/v1/pro/nutrition/targets'
      );
    });
  });

  describe('deduplication when base contains /api (no version)', () => {
    it('should deduplicate /api when base and path both contain it', () => {
      const base = 'http://localhost:8000/api';
      const path = '/api/files/x';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/files/x'
      );
    });

    it('should NOT deduplicate /api when path has /api/v1', () => {
      // base has /api, path has /api/v1 - different segments, no dedup
      const base = 'http://localhost:8000/api';
      const path = '/api/v1/files/x';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/api/v1/files/x'
      );
    });
  });

  describe('no deduplication when base does not contain /api', () => {
    it('should NOT deduplicate when base has no api segment', () => {
      const base = 'https://api.test.com';
      const path = '/api/v1/export.pdf';
      expect(normalizeApiUrl(base, path)).toBe(
        'https://api.test.com/api/v1/export.pdf'
      );
    });

    it('should work with simple base URL', () => {
      const base = 'http://localhost:8000';
      const path = '/api/v1/health';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/v1/health'
      );
    });
  });

  describe('edge cases', () => {
    it('should handle path without leading slash', () => {
      const base = 'http://localhost:8000/api/v1';
      const path = 'api/v1/files';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/v1/files'
      );
    });

    it('should handle empty path', () => {
      const base = 'http://localhost:8000/api/v1';
      const path = '';
      expect(normalizeApiUrl(base, path)).toBe(
        'http://localhost:8000/api/v1/'
      );
    });

    it('should fall back to naive concat for invalid base URL', () => {
      const base = 'not-a-url';
      const path = '/api/v1/test';
      expect(normalizeApiUrl(base, path)).toBe('not-a-url/api/v1/test');
    });
  });
});
