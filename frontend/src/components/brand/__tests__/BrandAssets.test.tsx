import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FitChefMascot, PulsePlateLogo } from '../..';

describe('brand assets', () => {
  it('renders the canonical PulsePlate logo variants', () => {
    render(
      <div>
        <PulsePlateLogo variant="mark" />
        <PulsePlateLogo tone="dark" variant="lockup" />
        <PulsePlateLogo variant="compact" />
      </div>
    );

    expect(screen.getByAltText('PulsePlate brand mark')).toBeInTheDocument();
    expect(screen.getByAltText('PulsePlate logo lockup')).toBeInTheDocument();
    expect(screen.getByAltText('PulsePlate compact logo')).toBeInTheDocument();
  });

  it('renders the FitChef mascot variants', () => {
    render(
      <div>
        <FitChefMascot variant="static" />
        <FitChefMascot variant="wink" />
        <FitChefMascot variant="neutral" />
        <FitChefMascot variant="thinking" />
        <FitChefMascot variant="sleepy" />
        <FitChefMascot variant="surprised" />
      </div>
    );

    expect(screen.getByAltText('FitChef mascot static variant')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef mascot wink portrait')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef mascot neutral portrait')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef mascot thinking portrait')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef mascot sleepy portrait')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef mascot surprised portrait')).toBeInTheDocument();
  });
});
