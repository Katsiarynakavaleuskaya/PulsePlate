/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { FormField } from '../FormField';
import { Textarea } from '../Textarea';

describe('Textarea', () => {
  it('updates its value', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    render(<Textarea aria-label="Planning notes" onChange={handleChange} />);

    await user.type(screen.getByRole('textbox', { name: 'Planning notes' }), 'Protein-first week');
    expect(handleChange).toHaveBeenCalled();
  });

  it('inherits form field error messaging', () => {
    render(
      <FormField
        error={{ message: 'Planning notes are required.' }}
        label="Planning notes"
        name="planning_notes"
      >
        <Textarea />
      </FormField>
    );

    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Planning notes are required.')).toBeInTheDocument();
  });
});
