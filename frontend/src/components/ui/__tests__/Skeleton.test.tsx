/** @vitest-environment jsdom */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton, ChartSkeleton, CardSkeleton, ProgressPageSkeleton } from '../Skeleton';

describe('Skeleton Components', () => {
  describe('Skeleton', () => {
    it('renders with default styles', () => {
      const { container } = render(<Skeleton />);

      const skeleton = container.firstChild as HTMLElement;
      expect(skeleton).toHaveClass('animate-pulse', 'rounded-md', 'bg-gray-300');
      expect(skeleton).toHaveClass('dark:bg-gray-700');
    });

    it('renders with custom className', () => {
      const { container } = render(<Skeleton className="w-10 h-10" />);

      const skeleton = container.firstChild as HTMLElement;
      expect(skeleton).toHaveClass('w-10', 'h-10');
    });
  });

  describe('ChartSkeleton', () => {
    it('renders chart skeleton structure', () => {
      render(<ChartSkeleton />);

      // Should have header skeleton and main chart skeleton
      const skeletons = screen.getAllByRole('generic');
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe('CardSkeleton', () => {
    it('renders card skeleton structure', () => {
      render(<CardSkeleton />);

      const skeletons = screen.getAllByRole('generic');
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe('ProgressPageSkeleton', () => {
    it('renders complete progress page skeleton', () => {
      render(<ProgressPageSkeleton />);

      const skeletons = screen.getAllByRole('generic');
      expect(skeletons.length).toBeGreaterThan(3); // header + charts + cards
    });
  });
});
