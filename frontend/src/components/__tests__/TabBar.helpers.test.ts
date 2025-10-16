import { describe, it, expect } from 'vitest';
import { getGridColsClass } from '../TabBar.helpers';

describe('TabBar.helpers', () => {
  describe('getGridColsClass', () => {
    const testCases: [number, string][] = [
      [1, 'grid-cols-1'],
      [2, 'grid-cols-2'],
      [3, 'grid-cols-3'],
      [4, 'grid-cols-4'],
      [5, 'grid-cols-5'],
      [6, 'grid-cols-6'],
      [0, 'grid-cols-3'],    // default/fallback
      [10, 'grid-cols-3'],   // default/fallback
      [-1, 'grid-cols-3'],   // default/fallback
    ];

    testCases.forEach(([input, expected]) => {
      it(`maps ${input} -> ${expected}`, () => {
        expect(getGridColsClass(input)).toBe(expected);
      });
    });
  });
});
