import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Home from '../Home';

describe('Home', () => {
  it('renders home page content', () => {
    render(<Home />);

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Скелет страницы.')).toBeInTheDocument();
  });

  it('has correct CSS classes', () => {
    render(<Home />);

    const main = screen.getByRole('main');
    expect(main).toHaveClass('p-4');
  });

  it('renders h1 heading', () => {
    render(<Home />);

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Home');
  });
});
