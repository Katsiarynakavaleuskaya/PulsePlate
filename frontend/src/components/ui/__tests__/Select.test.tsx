/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { FormField } from '../FormField';
import { Select } from '../Select';

describe('Select', () => {
  it('changes selected value', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(
      <Select
        aria-label="Meal slot"
        options={[
          { value: 'breakfast', label: 'Breakfast' },
          { value: 'lunch', label: 'Lunch' },
        ]}
        value="breakfast"
        onChange={handleChange}
      />
    );

    await user.selectOptions(screen.getByRole('combobox', { name: 'Meal slot' }), 'lunch');
    expect(handleChange).toHaveBeenCalled();
  });

  it('inherits error semantics through FormField', () => {
    render(
      <FormField
        error={{ type: 'validate', message: 'Choose a valid meal slot.' }}
        label="Meal slot"
        name="meal_slot"
      >
        <Select options={[{ value: 'lunch', label: 'Lunch' }]} value="lunch" onChange={() => {}} />
      </FormField>
    );

    expect(screen.getByRole('combobox')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Choose a valid meal slot.')).toHaveAttribute('role', 'alert');
  });
});
