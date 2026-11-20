import { describe, expect, it } from 'vitest';
import { cn } from '../utils';

describe('cn compatibility for existing component classes', () => {
  it('keeps the ChartSkeleton radius override', () => {
    expect(cn('rounded-md', 'rounded-lg')).toBe('rounded-lg');
  });

  it('changes height without dropping width', () => {
    expect(cn('h-8 w-48', 'h-10')).toBe('w-48 h-10');
  });

  it('keeps a later directional padding override', () => {
    expect(cn('p-4', 'px-6')).toBe('p-4 px-6');
  });

  it('lets later whole padding replace directional padding', () => {
    expect(cn('px-6', 'p-4')).toBe('p-4');
  });

  it('keeps dark background separate from a semantic base override', () => {
    expect(cn('bg-gray-300 dark:bg-gray-700', 'bg-[var(--color-surface)]'))
      .toBe('dark:bg-gray-700 bg-[var(--color-surface)]');
  });

  it('keeps a responsive radius separate from the base radius', () => {
    expect(cn('rounded-md md:rounded-lg', 'rounded-xl')).toBe('md:rounded-lg rounded-xl');
  });

  it('retains clsx filtering and unrelated motion/custom classes', () => {
    expect(cn(['motion-safe:animate-pulse', false], { 'custom-class': true }, undefined))
      .toBe('motion-safe:animate-pulse custom-class');
  });
});
