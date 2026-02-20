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
    expect(screen.getByRole('link', { name: 'Open progress live' })).toHaveAttribute('href', '/progress');
    expect(screen.getByText('Quick actions')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open setup' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open plate' })).toHaveAttribute('href', '/plate');
    expect(screen.getByRole('link', { name: 'Open progress' })).toHaveAttribute('href', '/progress');
    expect(screen.getByRole('link', { name: 'Open Pro' })).toHaveAttribute('href', '/pro');
  });

  it('has correct CSS classes', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('p-4');
    expect(main).toHaveClass('pb-24');
  });

});
