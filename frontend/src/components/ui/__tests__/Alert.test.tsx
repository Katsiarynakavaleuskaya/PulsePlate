/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Button } from '../Button';
import { Alert } from '../Alert';

describe('Alert', () => {
  it('uses status role for success surfaces', () => {
    render(<Alert tone="success">Review lane synced</Alert>);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('uses alert role for warning surfaces', () => {
    render(<Alert tone="warning">One required field is missing</Alert>);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders optional actions', () => {
    render(
      <Alert action={<Button size="sm">Review</Button>} title="Needs attention" tone="warning">
        One required field is missing.
      </Alert>
    );

    expect(screen.getByRole('button', { name: 'Review' })).toBeInTheDocument();
  });
});
