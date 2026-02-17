import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Profile from '../Profile';

describe('Profile', () => {

  it('renders profile page content', () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Profile' })).toBeInTheDocument();
    expect(screen.getByText('Environment status')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configure API key' })).toBeInTheDocument();
  });

  it('has correct CSS classes', () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('p-4');
    expect(main).toHaveClass('pb-24');
  });

  it('renders h1 heading', () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Profile');
  });
});
