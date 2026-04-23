import type { PropsWithChildren } from 'react';
import {
  Tab as HeadlessTab,
  TabGroup,
  TabList as HeadlessTabList,
  TabPanel as HeadlessTabPanel,
  TabPanels as HeadlessTabPanels,
} from '@headlessui/react';

interface TabsProps extends PropsWithChildren {
  defaultIndex?: number;
  selectedIndex?: number;
  onChange?: (index: number) => void;
}

interface TabsListProps extends PropsWithChildren {
  className?: string;
}

interface TabsTriggerProps extends PropsWithChildren {
  className?: string;
  disabled?: boolean;
}

interface TabsPanelsProps extends PropsWithChildren {
  className?: string;
}

interface TabsPanelProps extends PropsWithChildren {
  className?: string;
}

export function Tabs({ children, defaultIndex = 0, selectedIndex, onChange }: TabsProps) {
  return (
    <TabGroup defaultIndex={defaultIndex} selectedIndex={selectedIndex} onChange={onChange}>
      {children}
    </TabGroup>
  );
}

export function TabsList({ children, className = '' }: TabsListProps) {
  return (
    <HeadlessTabList
      className={[
        'flex flex-wrap gap-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-2',
        className,
      ]
        .join(' ')
        .trim()}
    >
      {children}
    </HeadlessTabList>
  );
}

export function TabsTrigger({ children, className = '', disabled = false }: TabsTriggerProps) {
  return (
    <HeadlessTab
      className={({ selected }) =>
        [
          'rounded-xl px-4 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-1',
          selected
            ? 'bg-[var(--color-primary)] text-[var(--color-primary-foreground)] shadow-sm'
            : 'bg-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-text)]',
          disabled ? 'cursor-not-allowed opacity-60' : '',
          className,
        ]
          .join(' ')
          .trim()
      }
      disabled={disabled}
    >
      {children}
    </HeadlessTab>
  );
}

export function TabsPanels({ children, className = '' }: TabsPanelsProps) {
  return <HeadlessTabPanels className={['mt-4', className].join(' ').trim()}>{children}</HeadlessTabPanels>;
}

export function TabsPanel({ children, className = '' }: TabsPanelProps) {
  return (
    <HeadlessTabPanel
      className={[
        'rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-[var(--color-text)] focus:outline-none',
        className,
      ]
        .join(' ')
        .trim()}
    >
      {children}
    </HeadlessTabPanel>
  );
}

export default Tabs;
