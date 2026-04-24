/** @vitest-environment jsdom */
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { Alert } from '../Alert';
import { Badge } from '../Badge';
import { Checkbox } from '../Checkbox';
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuItems,
  DropdownMenuTrigger,
} from '../DropdownMenu';
import { Hero } from '../Hero';
import { ProgressIndicator } from '../ProgressIndicator';
import { RadioGroup, RadioGroupOption } from '../RadioGroup';
import { StatsCard } from '../StatsCard';
import { Stepper } from '../Stepper';
import { Tabs, TabsList, TabsPanel, TabsPanels, TabsTrigger } from '../Tabs';
import { Tooltip } from '../Tooltip';
import { Button } from '../Button';

describe('new governed primitives accessibility', () => {
  it('renders checkbox and radio group without axe violations', async () => {
    const { container } = render(
      <div>
        <label>
          <Checkbox checked={true} onChange={() => {}} />
          <span>Weekly planning summary</span>
        </label>
        <RadioGroup legend="Coaching tone">
          <RadioGroupOption checked={true} label="Calm" name="coaching-tone" value="calm" onChange={() => {}} />
          <RadioGroupOption checked={false} label="Motivated" name="coaching-tone" value="motivated" onChange={() => {}} />
        </RadioGroup>
      </div>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('renders alert, tabs, dropdown menu, and tooltip without axe violations', async () => {
    const { container } = render(
      <div>
        <Alert tone="success">Review lane synced</Alert>
        <Tabs>
          <TabsList>
            <TabsTrigger>Overview</TabsTrigger>
            <TabsTrigger>States</TabsTrigger>
          </TabsList>
          <TabsPanels>
            <TabsPanel>
              <p>Overview panel</p>
            </TabsPanel>
            <TabsPanel>
              <p>States panel</p>
            </TabsPanel>
          </TabsPanels>
        </Tabs>
        <DropdownMenu>
          <DropdownMenuTrigger>More actions</DropdownMenuTrigger>
          <DropdownMenuItems>
            <DropdownMenuItem>Duplicate</DropdownMenuItem>
          </DropdownMenuItems>
        </DropdownMenu>
        <Tooltip content="Supportive helper copy">
          <Button size="sm">Why this matters</Button>
        </Tooltip>
      </div>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('renders normalized families without axe violations', async () => {
    const { container } = render(
      <div>
        <Badge tone="premium">VIP</Badge>
        <Hero
          chips={<span>Session Connected</span>}
          description="Quick actions and premium guidance."
          eyebrow="Calm control panel"
          title="PulsePlate Home"
        />
        <ProgressIndicator
          action={<Button size="sm">Open progress</Button>}
          description="Shared progress anatomy"
          label="Live updates on"
          state="live"
          timestampLabel="7:00 PM"
        />
        <StatsCard detail="Secure session status" label="Connection" value="Connected" />
        <Stepper
          ariaLabel="Setup progress"
          currentStep={0}
          progressLabel="Step 1 of 2"
          steps={[
            { id: 'profile', label: 'Profile', description: 'Capture your nutrition inputs' },
            { id: 'results', label: 'Results', description: 'Review macros and targets' },
          ]}
        />
      </div>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
