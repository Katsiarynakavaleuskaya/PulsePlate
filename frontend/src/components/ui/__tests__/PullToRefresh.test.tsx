/** @vitest-environment jsdom */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, cleanup } from '@testing-library/react';
import { PullToRefresh } from '../PullToRefresh';

describe('PullToRefresh', () => {
  const mockOnRefresh = vi.fn();

  beforeEach(() => {
    mockOnRefresh.mockClear();
  });

  afterEach(() => {
    cleanup();
  });


  it('renders children correctly', () => {
    render(
      <PullToRefresh onRefresh={mockOnRefresh}>
        <div>Test content</div>
      </PullToRefresh>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('calls onRefresh when pulled beyond threshold', async () => {
    mockOnRefresh.mockResolvedValue(undefined);

    render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={50}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const container = screen.getAllByText('Test content')[0].closest('[class*="relative"]')!;

    // Simulate touch start
    await act(async () => {
      fireEvent.touchStart(container, {
        touches: [{ clientY: 100 }]
      });
    });

    // Simulate touch move (pull down 100px)
    await act(async () => {
      fireEvent.touchMove(container, {
        touches: [{ clientY: 200 }]
      });
    });

    // Simulate touch end
    await act(async () => {
      fireEvent.touchEnd(container);
    });

    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('does not call onRefresh when pulled below threshold', () => {
    render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={50}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const container = screen.getAllByText('Test content')[0].closest('[class*="relative"]')!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientY: 100 }]
    });

    // Simulate touch move (pull down only 20px - below threshold)
    fireEvent.touchMove(container, {
      touches: [{ clientY: 120 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });

  it('does not trigger when disabled', () => {
    render(
      <PullToRefresh onRefresh={mockOnRefresh} disabled>
        <div>Test content</div>
      </PullToRefresh>
    );

    const container = screen.getAllByText('Test content')[0].closest('[class*="relative"]')!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientY: 100 }]
    });

    // Simulate touch move
    fireEvent.touchMove(container, {
      touches: [{ clientY: 200 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });

  it('respects custom threshold', () => {
    render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={100}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const container = screen.getAllByText('Test content')[0].closest('[class*="relative"]')!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientY: 100 }]
    });

    // Simulate touch move (pull down 60px - below custom threshold of 100)
    fireEvent.touchMove(container, {
      touches: [{ clientY: 160 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });
});
