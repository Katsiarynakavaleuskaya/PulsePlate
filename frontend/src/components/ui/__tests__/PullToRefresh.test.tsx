/** @vitest-environment jsdom */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PullToRefresh } from '../PullToRefresh';

describe('PullToRefresh', () => {
  const mockOnRefresh = vi.fn();

  beforeEach(() => {
    mockOnRefresh.mockClear();
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

    const container = screen.getByText('Test content').parentElement!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientY: 100 }]
    });

    // Simulate touch move (pull down 100px)
    fireEvent.touchMove(container, {
      touches: [{ clientY: 200 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    // Wait for the async operation
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
  });

  it('does not call onRefresh when pulled below threshold', () => {
    render(
      <PullToRefresh onRefresh={mockOnRefresh} threshold={50}>
        <div>Test content</div>
      </PullToRefresh>
    );

    const container = screen.getByText('Test content').parentElement!;

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

    const container = screen.getByText('Test content').parentElement!;

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

    const container = screen.getByText('Test content').parentElement!;

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
