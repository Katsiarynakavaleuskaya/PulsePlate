import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Home from '../Home';

describe('Home', () => {
  it('renders home page content', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Home' })).toBeInTheDocument();
    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View detailed progress' })).toHaveAttribute('href', '/progress');
    expect(screen.getByText('Quick Navigation')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configure Setup' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nutrition Plate' })).toHaveAttribute('href', '/plate');
    expect(screen.getByRole('link', { name: 'Progress View' })).toHaveAttribute('href', '/progress');
    expect(screen.getByRole('link', { name: 'Premium Features' })).toHaveAttribute('href', '/pro');
  });

  it('has correct CSS classes', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('flex');
    expect(main).toHaveClass('min-h-screen');
    expect(main).toHaveClass('flex-col');
    expect(main).toHaveClass('bg-[var(--color-bg)]');
  });

});
