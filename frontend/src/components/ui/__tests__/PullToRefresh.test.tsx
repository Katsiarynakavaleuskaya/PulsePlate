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

    const { container } = render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={50}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const first = container.firstChild;
    if (!first) throw new Error('Container element not found');
    const pullToRefreshContainer = first as HTMLElement;

    // Simulate touch start
    await act(async () => {
      fireEvent.touchStart(pullToRefreshContainer, {
        touches: [{ clientY: 100 }],
      });
    });

    // Simulate touch move (pull down 100px)
    await act(async () => {
      fireEvent.touchMove(pullToRefreshContainer, {
        touches: [{ clientY: 200 }],
      });
    });

    // Simulate touch end
    await act(async () => {
      fireEvent.touchEnd(pullToRefreshContainer);
    });

    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('does not call onRefresh when pulled below threshold', () => {
    const { container } = render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={50}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const first = container.firstChild;
    if (!first) throw new Error('Container element not found');
    const pullToRefreshContainer = first as HTMLElement;

    // Simulate touch start
    fireEvent.touchStart(pullToRefreshContainer, {
      touches: [{ clientY: 100 }],
    });

    // Simulate touch move (pull down only 20px - below threshold)
    fireEvent.touchMove(pullToRefreshContainer, {
      touches: [{ clientY: 120 }],
    });

    // Simulate touch end
    fireEvent.touchEnd(pullToRefreshContainer);

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });

  it('does not trigger when disabled', () => {
    const { container } = render(
      <PullToRefresh onRefresh={mockOnRefresh} disabled>
        <div>Test content</div>
      </PullToRefresh>
    );

    const first = container.firstChild;
    if (!first) throw new Error('Container element not found');
    const pullToRefreshContainer = first as HTMLElement;

    // Simulate touch start
    fireEvent.touchStart(pullToRefreshContainer, {
      touches: [{ clientY: 100 }],
    });

    // Simulate touch move
    fireEvent.touchMove(pullToRefreshContainer, {
      touches: [{ clientY: 200 }],
    });

    // Simulate touch end
    fireEvent.touchEnd(pullToRefreshContainer);

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });

  it('respects custom threshold', () => {
    const { container } = render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={100}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const first = container.firstChild;
    if (!first) throw new Error('Container element not found');
    const pullToRefreshContainer = first as HTMLElement;

    // Simulate touch start
    fireEvent.touchStart(pullToRefreshContainer, {
      touches: [{ clientY: 100 }],
    });

    // Simulate touch move (pull down 60px - below custom threshold of 100)
    fireEvent.touchMove(pullToRefreshContainer, {
      touches: [{ clientY: 160 }],
    });

    // Simulate touch end
    fireEvent.touchEnd(pullToRefreshContainer);

    expect(mockOnRefresh).not.toHaveBeenCalled();
  });
});
