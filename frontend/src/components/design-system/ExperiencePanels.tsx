import { Button, Input, Toggle } from '../ui';
import { forbiddenDirections, governanceLocks, platformScreens } from './data';
import { PanelShell } from './shared';

interface ComponentShowcasePanelProps {
  notificationsEnabled: boolean;
  onNotificationsChange: (enabled: boolean) => void;
}

export function ComponentShowcasePanel({
  notificationsEnabled,
  onNotificationsChange,
}: ComponentShowcasePanelProps) {
  return (
    <PanelShell title="Shared Components" subtitle="Current primitives shown in Storybook-first review flow">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.02] p-4">
          <Button className="w-full rounded-full bg-[var(--pp-blue)] px-6 py-3 text-white shadow-[0_16px_40px_rgba(51,159,255,0.22)]">
            Start Setup
          </Button>
          <Button
            variant="secondary"
            className="w-full rounded-full border-white/12 bg-white/[0.04] px-6 py-3 text-white hover:bg-white/[0.08]"
          >
            View Progress
          </Button>
          <button
            type="button"
            className="w-full rounded-full border border-[rgba(255,93,93,0.18)] bg-[rgba(255,93,93,0.1)] px-6 py-3 text-sm font-semibold text-[var(--pp-red)]"
          >
            Critical Alert State
          </button>
        </div>
        <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.02] p-4">
          <Input
            aria-label="Design system showcase input"
            className="rounded-2xl border-white/10 bg-white/[0.04] px-4 py-3 text-white placeholder:text-white/30"
            defaultValue="Protein-first lunch planning"
            placeholder="Enter your daily focus"
          />
          <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <Toggle
              checked={notificationsEnabled}
              label="Enable check-in reminders"
              onChange={onNotificationsChange}
            />
          </div>
          <div className="rounded-2xl border border-[rgba(32,201,151,0.16)] bg-[rgba(32,201,151,0.09)] p-4">
            <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--pp-green)]">Success Surface</p>
            <p className="mt-2 text-sm text-white/75">
              Gentle feedback keeps the product supportive and lifestyle-centered rather than diagnostic.
            </p>
          </div>
        </div>
      </div>
    </PanelShell>
  );
}

export function PlatformInventoryPanel() {
  return (
    <PanelShell title="Platform Inventory" subtitle="Current design-system coverage across surfaces">
      <div className="grid gap-4 lg:grid-cols-3">
        {platformScreens.map((group) => (
          <div key={group.platform} className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">{group.platform}</p>
            <ul className="mt-3 space-y-2">
              {group.screens.map((screenName) => (
                <li
                  key={screenName}
                  className="flex items-center gap-3 rounded-xl border border-white/6 bg-white/[0.02] px-3 py-2 text-sm text-white/72"
                >
                  <span
                    className={[
                      'inline-flex min-w-[38px] items-center justify-center rounded-md px-2 py-1 text-[10px] uppercase tracking-[0.18em]',
                      group.platform === 'Web'
                        ? 'bg-[rgba(32,201,151,0.15)] text-[var(--pp-green)]'
                        : group.platform === 'iOS'
                          ? 'bg-[rgba(51,159,255,0.15)] text-[var(--pp-blue)]'
                          : 'bg-white/[0.09] text-white/55',
                    ].join(' ')}
                  >
                    {group.platform}
                  </span>
                  <span>{screenName}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </PanelShell>
  );
}

export function GovernancePanel() {
  return (
    <PanelShell title="Governance" subtitle="Anti-drift constraints and immutable locks">
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-white/35">Forbidden Directions</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {forbiddenDirections.map((item) => (
              <div
                key={item}
                className="flex items-center gap-3 rounded-xl border border-[rgba(255,93,93,0.14)] bg-[rgba(255,93,93,0.05)] px-4 py-3 text-sm text-white/70"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--pp-red)]" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-white/35">Governance Locks</p>
          <ul className="mt-3 space-y-3">
            {governanceLocks.map((lock) => (
              <li key={lock.text} className="flex items-start gap-3 rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
                <span className={`mt-1 h-2.5 w-2.5 rounded-full ${lock.toneClass}`} />
                <span className="text-sm text-white/72">{lock.text}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </PanelShell>
  );
}
