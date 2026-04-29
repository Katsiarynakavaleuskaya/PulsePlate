/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProgressIndicator } from '../ProgressIndicator';

describe('ProgressIndicator', () => {
  it('uses reduced-motion-safe live indicator motion', () => {
    render(<ProgressIndicator label="Syncing" state="live" />);

    const liveLabel = screen.getByText('Live status');
    expect(liveLabel).toHaveClass('sr-only');
    expect(liveLabel.previousSibling).toHaveClass('motion-safe:animate-pulse');
  });

  it('exposes non-color-only warning semantics', () => {
    render(<ProgressIndicator label="Review needed" state="warning" />);

    expect(screen.getByText('Warning status')).toHaveClass('sr-only');
    expect(screen.getByText('Review needed')).toBeInTheDocument();
  });
});
