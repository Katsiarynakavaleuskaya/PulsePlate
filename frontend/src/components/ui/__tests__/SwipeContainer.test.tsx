/** @vitest-environment jsdom */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SwipeContainer } from '../SwipeContainer';

describe('SwipeContainer', () => {
  const mockOnSwipeLeft = vi.fn();
  const mockOnSwipeRight = vi.fn();

  beforeEach(() => {
    mockOnSwipeLeft.mockClear();
    mockOnSwipeRight.mockClear();
  });

  it('renders children correctly', () => {
    render(
      <SwipeContainer>
        <div>Test content</div>
      </SwipeContainer>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('calls onSwipeRight when swiped right beyond threshold', () => {
    render(
      <SwipeContainer onSwipeRight={mockOnSwipeRight} threshold={50}>
        <div>Test content</div>
      </SwipeContainer>
    );

    const container = screen.getByText('Test content').parentElement!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientX: 100 }]
    });

    // Simulate touch move (swipe right by 60px - beyond threshold)
    fireEvent.touchMove(container, {
      touches: [{ clientX: 160 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnSwipeRight).toHaveBeenCalledTimes(1);
    expect(mockOnSwipeLeft).not.toHaveBeenCalled();
  });

  it('calls onSwipeLeft when swiped left beyond threshold', () => {
    render(
      <SwipeContainer onSwipeLeft={mockOnSwipeLeft} threshold={50}>
        <div>Test content</div>
      </SwipeContainer>
    );

    const container = screen.getByText('Test content').parentElement!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientX: 100 }]
    });

    // Simulate touch move (swipe left by 60px - beyond threshold)
    fireEvent.touchMove(container, {
      touches: [{ clientX: 40 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnSwipeLeft).toHaveBeenCalledTimes(1);
    expect(mockOnSwipeRight).not.toHaveBeenCalled();
  });

  it('does not call swipe handlers when swipe is below threshold', () => {
    render(
      <SwipeContainer onSwipeLeft={mockOnSwipeLeft} onSwipeRight={mockOnSwipeRight} threshold={50}>
        <div>Test content</div>
      </SwipeContainer>
    );

    const container = screen.getByText('Test content').parentElement!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientX: 100 }]
    });

    // Simulate touch move (swipe right by only 30px - below threshold)
    fireEvent.touchMove(container, {
      touches: [{ clientX: 130 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnSwipeLeft).not.toHaveBeenCalled();
    expect(mockOnSwipeRight).not.toHaveBeenCalled();
  });

  it('respects custom threshold', () => {
    render(
      <SwipeContainer onSwipeRight={mockOnSwipeRight} threshold={100}>
        <div>Test content</div>
      </SwipeContainer>
    );

    const container = screen.getByText('Test content').parentElement!;

    // Simulate touch start
    fireEvent.touchStart(container, {
      touches: [{ clientX: 100 }]
    });

    // Simulate touch move (swipe right by 80px - below custom threshold of 100)
    fireEvent.touchMove(container, {
      touches: [{ clientX: 180 }]
    });

    // Simulate touch end
    fireEvent.touchEnd(container);

    expect(mockOnSwipeRight).not.toHaveBeenCalled();
  });

  it('handles both swipe directions', () => {
    render(
      <SwipeContainer onSwipeLeft={mockOnSwipeLeft} onSwipeRight={mockOnSwipeRight} threshold={50}>
        <div>Test content</div>
      </SwipeContainer>
    );

    const container = screen.getByText('Test content').parentElement!;

    // Test swipe right
    fireEvent.touchStart(container, { touches: [{ clientX: 100 }] });
    fireEvent.touchMove(container, { touches: [{ clientX: 160 }] });
    fireEvent.touchEnd(container);

    expect(mockOnSwipeRight).toHaveBeenCalledTimes(1);

    // Test swipe left
    fireEvent.touchStart(container, { touches: [{ clientX: 100 }] });
    fireEvent.touchMove(container, { touches: [{ clientX: 40 }] });
    fireEvent.touchEnd(container);

    expect(mockOnSwipeLeft).toHaveBeenCalledTimes(1);
  });
});
