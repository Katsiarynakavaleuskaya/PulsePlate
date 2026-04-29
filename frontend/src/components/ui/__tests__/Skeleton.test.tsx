/** @vitest-environment jsdom */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton, ChartSkeleton, CardSkeleton, ProgressPageSkeleton } from '../Skeleton';

describe('Skeleton Components', () => {
  describe('Skeleton', () => {
    it('renders with default styles', () => {
      const { container } = render(<Skeleton />);

      const skeleton = container.firstChild as HTMLElement;
      expect(skeleton).toHaveClass('motion-safe:animate-pulse', 'rounded-md', 'bg-gray-300');
      expect(skeleton).toHaveClass('dark:bg-gray-700');
      expect(skeleton).toHaveAttribute('aria-hidden', 'true');
    });

    it('renders with custom className', () => {
      const { container } = render(<Skeleton className="w-10 h-10" />);

      const skeleton = container.firstChild as HTMLElement;
      expect(skeleton).toHaveClass('w-10', 'h-10');
    });

    it('can expose labeled status semantics when requested', () => {
      render(<Skeleton ariaLabel="Loading dashboard" />);

      const skeleton = screen.getByRole('status', { name: 'Loading dashboard' });
      expect(skeleton).toHaveAttribute('aria-live', 'polite');
      expect(skeleton).not.toHaveAttribute('aria-hidden');
    });
  });

  describe('ChartSkeleton', () => {
    it('renders chart skeleton structure', () => {
      render(<ChartSkeleton />);

      // Should have header skeleton and main chart skeleton
      const skeletons = document.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe('CardSkeleton', () => {
    it('renders card skeleton structure', () => {
      render(<CardSkeleton />);

      const skeletons = document.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe('ProgressPageSkeleton', () => {
    it('renders complete progress page skeleton', () => {
      render(<ProgressPageSkeleton />);

      const skeletons = document.querySelectorAll('[aria-hidden="true"]');
      expect(skeletons.length).toBeGreaterThan(3); // header + charts + cards
    });
  });
});
