/**
 * Design Tokens Tests
 *
 * Tests for design token consistency, type safety, and value validation.
 */

import fs from 'node:fs';
import path from 'node:path';
import { describe, it, expect } from 'vitest';
import {
  colors,
  spacing,
  typography,
  borderRadius,
  shadows,
  breakpoints,
  zIndex,
  type ColorScale,
  type SpacingKey,
  type TypographySize,
  type TypographyWeight,
} from '../tokens';

describe('Design Tokens', () => {
  describe('Colors', () => {
    it('should have consistent color scales', () => {
      const colorScales = ['navy', 'blue', 'green', 'heart', 'gray'] as const;

      colorScales.forEach(scale => {
        const colorScale = colors[scale];
        expect(colorScale).toBeDefined();

        // Check that all scales have the same keys
        const expectedKeys = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'];
        const actualKeys = Object.keys(colorScale);
        expect(actualKeys).toEqual(expectedKeys);
      });
    });

    it('should have valid hex color values', () => {
      const allColors = [
        ...Object.values(colors.navy),
        ...Object.values(colors.blue),
        ...Object.values(colors.green),
        ...Object.values(colors.heart),
        ...Object.values(colors.gray),
        ...Object.values(colors.semantic),
      ];

      allColors.forEach(color => {
        expect(color).toMatch(/^#[0-9a-fA-F]{6}$/);
      });
    });

    it('should have semantic colors defined', () => {
      expect(colors.semantic.success).toBeDefined();
      expect(colors.semantic.warning).toBeDefined();
      expect(colors.semantic.error).toBeDefined();
      expect(colors.semantic.info).toBeDefined();
    });

    it('should have proper color progression (darker to lighter)', () => {
      // 500 should be the base color
      expect(colors.navy[500]).toBe('#627d98'); // navy-500

      // Higher numbers should be darker
      expect(colors.navy[600]).toBe('#486581'); // navy-600
      expect(colors.navy[700]).toBe('#334e68'); // navy-700
    });
  });

  describe('Spacing', () => {
    it('should have consistent spacing scale', () => {
      const expectedSpacing = {
        0: '0',
        1: '0.25rem',
        2: '0.5rem',
        3: '0.75rem',
        4: '1rem',
        5: '1.25rem',
        6: '1.5rem',
        8: '2rem',
        10: '2.5rem',
        12: '3rem',
        16: '4rem',
        20: '5rem',
        24: '6rem',
      };

      Object.entries(expectedSpacing).forEach(([key, value]) => {
        expect(spacing[key as SpacingKey]).toBe(value);
      });
    });

    it('should have touch-friendly targets', () => {
      expect(spacing.touch).toBe('2.75rem'); // 44px
      expect(spacing.touchLarge).toBe('3.5rem'); // 56px
    });

    it('should have component-specific spacing', () => {
      expect(spacing.button.sm).toBe('0.5rem 1rem');
      expect(spacing.button.md).toBe('0.75rem 1.5rem');
      expect(spacing.button.lg).toBe('1rem 2rem');

      expect(spacing.input.sm).toBe('0.5rem 0.75rem');
      expect(spacing.input.md).toBe('0.75rem 1rem');
      expect(spacing.input.lg).toBe('1rem 1.25rem');
    });
  });

  describe('Typography', () => {
    it('should have consistent font sizes', () => {
      const expectedSizes = {
        xs: '0.75rem',
        sm: '0.875rem',
        base: '1rem',
        lg: '1.125rem',
        xl: '1.25rem',
        '2xl': '1.5rem',
        '3xl': '1.875rem',
        '4xl': '2.25rem',
        '5xl': '3rem',
      };

      Object.entries(expectedSizes).forEach(([key, value]) => {
        expect(typography.fontSize[key as TypographySize]).toBe(value);
      });
    });

    it('should have proper font weights', () => {
      expect(typography.fontWeight.light).toBe('300');
      expect(typography.fontWeight.normal).toBe('400');
      expect(typography.fontWeight.medium).toBe('500');
      expect(typography.fontWeight.semibold).toBe('600');
      expect(typography.fontWeight.bold).toBe('700');
    });

    it('should have text styles defined', () => {
      expect(typography.textStyles.heading).toBeDefined();
      expect(typography.textStyles.body).toBeDefined();
      expect(typography.textStyles.caption).toBeDefined();
    });

    it('should have proper line heights', () => {
      expect(typography.lineHeight.tight).toBe('1.25');
      expect(typography.lineHeight.normal).toBe('1.5');
      expect(typography.lineHeight.loose).toBe('2');
    });
  });

  describe('Border Radius', () => {
    it('should have consistent radius values', () => {
      expect(borderRadius.none).toBe('0px');
      expect(borderRadius.sm).toBe('0.125rem');
      expect(borderRadius.base).toBe('0.25rem');
      expect(borderRadius.md).toBe('0.375rem');
      expect(borderRadius.lg).toBe('0.5rem');
      expect(borderRadius.xl).toBe('0.75rem');
      expect(borderRadius['2xl']).toBe('1rem');
      expect(borderRadius.full).toBe('9999px');
    });
  });

  describe('Shadows', () => {
    it('should have defined shadow values', () => {
      expect(shadows.sm).toBeDefined();
      expect(shadows.base).toBeDefined();
      expect(shadows.md).toBeDefined();
      expect(shadows.lg).toBeDefined();
      expect(shadows.xl).toBeDefined();
    });

    it('should have valid shadow syntax', () => {
      Object.values(shadows).forEach(shadow => {
        expect(shadow).toMatch(/^0 \d+px \d+px/);
      });
    });

    it('should retain destructive compatibility aliases in runtime CSS', () => {
      const cssPath = path.resolve(__dirname, '../tokens.css');
      const css = fs.readFileSync(cssPath, 'utf8');

      expect(css).toContain('--color-destructive-bg:');
      expect(css).toContain('--color-destructive-bg-hover:');
      expect(css).toContain('--color-destructive-border:');
      expect(css).toContain('--shadow-destructive:');
    });
  });

  describe('Breakpoints', () => {
    it('should have responsive breakpoints', () => {
      expect(breakpoints.sm).toBe('640px');
      expect(breakpoints.md).toBe('768px');
      expect(breakpoints.lg).toBe('1024px');
      expect(breakpoints.xl).toBe('1280px');
      expect(breakpoints['2xl']).toBe('1536px');
    });

    it('should have proper breakpoint progression', () => {
      const values = Object.values(breakpoints).map(v => parseInt(v));
      for (let i = 1; i < values.length; i++) {
        expect(values[i]).toBeGreaterThan(values[i - 1]);
      }
    });
  });

  describe('Z-Index', () => {
    it('should have proper z-index hierarchy', () => {
      expect(zIndex.hide).toBe(-1);
      expect(zIndex.base).toBe(0);
      expect(zIndex.dropdown).toBe(1000);
      expect(zIndex.modal).toBe(1400);
      expect(zIndex.tooltip).toBe(1800);
    });

    it('should have logical z-index progression', () => {
      const values = Object.values(zIndex).filter(v => typeof v === 'number') as number[];
      for (let i = 1; i < values.length; i++) {
        expect(values[i]).toBeGreaterThanOrEqual(values[i - 1]);
      }
    });
  });

  describe('Type Safety', () => {
    it('should have proper TypeScript types', () => {
      // These should compile without errors
      const colorScale: ColorScale = 500;
      const spacingKey: SpacingKey = 4;
      const fontSize: TypographySize = 'lg';
      const fontWeight: TypographyWeight = 'semibold';

      expect(colorScale).toBe(500);
      expect(spacingKey).toBe(4);
      expect(fontSize).toBe('lg');
      expect(fontWeight).toBe('semibold');
    });
  });

  describe('Accessibility', () => {
    // Helper function to convert hex to RGB
    const hexToRgb = (hex: string): [number, number, number] => {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      if (!result) throw new Error(`Invalid hex color: ${hex}`);
      return [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
      ];
    };

    // Helper function to calculate relative luminance
    const getLuminance = (r: number, g: number, b: number): number => {
      const [rs, gs, bs] = [r, g, b].map(c => {
        c = c / 255;
        return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    };

    // Helper function to calculate contrast ratio
    const getContrastRatio = (color1: string, color2: string): number => {
      const [r1, g1, b1] = hexToRgb(color1);
      const [r2, g2, b2] = hexToRgb(color2);
      const lum1 = getLuminance(r1, g1, b1);
      const lum2 = getLuminance(r2, g2, b2);
      const brightest = Math.max(lum1, lum2);
      const darkest = Math.min(lum1, lum2);
      return (brightest + 0.05) / (darkest + 0.05);
    };

    it('should have sufficient color contrast ratios', () => {
      // Test that navy-600 on white has good contrast (WCAG AA >= 4.5)
      const navy600 = colors.navy[600];
      const white = '#ffffff';

      expect(navy600).toBeDefined();
      expect(white).toBeDefined();

      const contrastRatio = getContrastRatio(navy600, white);
      expect(contrastRatio).toBeGreaterThanOrEqual(4.5);

      // Test that navy-50 on navy-900 has good contrast
      const navy50 = colors.navy[50];
      const navy900 = colors.navy[900];
      const darkContrastRatio = getContrastRatio(navy50, navy900);
      expect(darkContrastRatio).toBeGreaterThanOrEqual(4.5);
    });

    it('should have touch-friendly spacing', () => {
      // Touch targets should be at least 44px
      const touchTarget = parseFloat(spacing.touch.replace('rem', ''));
      expect(touchTarget).toBeGreaterThanOrEqual(2.75); // 44px in rem
    });
  });
});
