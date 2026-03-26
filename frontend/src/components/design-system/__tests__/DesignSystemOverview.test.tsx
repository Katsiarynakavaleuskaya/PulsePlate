import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DesignSystemOverview } from '../..';

describe('DesignSystemOverview', () => {
  it('renders the Storybook-first design system sections', () => {
    render(<DesignSystemOverview />);

    expect(screen.getByRole('heading', { level: 1, name: 'PulsePlate Design System' })).toBeInTheDocument();
    expect(screen.getByText('Identity Fields')).toBeInTheDocument();
    expect(screen.getByText('Brand Palette')).toBeInTheDocument();
    expect(screen.getByText('Typography')).toBeInTheDocument();
    expect(screen.getByText('Shared Components')).toBeInTheDocument();
    expect(screen.getByText('Platform Inventory')).toBeInTheDocument();
    expect(screen.getByText('Governance')).toBeInTheDocument();
    expect(screen.getByText('Figma documentation boards with runtime-safe assets')).toBeInTheDocument();
    expect(screen.getByText('PP iOS Foundation Tokens v1')).toBeInTheDocument();
    expect(screen.getByText('PP Brand + FitChef Logo Canon v1')).toBeInTheDocument();
    expect(screen.getByText('Onboarding Welcome')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef onboarding welcome scene')).toBeInTheDocument();
  });
});
