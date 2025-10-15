import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Profile from '../Profile';

describe('Profile', () => {

  it('renders profile page content', () => {
    render(<Profile />);

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Скелет страницы.')).toBeInTheDocument();
  });

  it('has correct CSS classes', () => {
    render(<Profile />);

    const main = screen.getByRole('main');
    expect(main).toHaveClass('p-4');
  });

  it('renders h1 heading', () => {
    render(<Profile />);

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Profile');
  });
});
