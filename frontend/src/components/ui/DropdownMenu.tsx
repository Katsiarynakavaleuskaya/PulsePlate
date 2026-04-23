import { Fragment } from 'react';
import type { AnchorHTMLAttributes, ButtonHTMLAttributes, PropsWithChildren, ReactElement, ReactNode } from 'react';
import { Menu, MenuButton, MenuItem, MenuItems, Transition } from '@headlessui/react';
import { ChevronDown } from 'lucide-react';
import { buttonClasses } from './Button';

interface DropdownMenuProps extends PropsWithChildren {
  className?: string;
}

interface DropdownMenuTriggerProps extends PropsWithChildren {
  className?: string;
}

interface DropdownMenuItemsProps extends PropsWithChildren {
  align?: 'start' | 'end';
}

interface DropdownMenuItemProps extends PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>> {
  destructive?: boolean;
  icon?: ReactNode;
}

interface DropdownMenuLinkItemProps extends PropsWithChildren<AnchorHTMLAttributes<HTMLAnchorElement>> {
  destructive?: boolean;
  icon?: ReactNode;
}

export function DropdownMenu({ children, className = '' }: DropdownMenuProps): ReactElement {
  return <Menu as="div" className={['relative inline-block text-left', className].join(' ').trim()}>{children}</Menu>;
}

export function DropdownMenuTrigger({ children, className = '' }: DropdownMenuTriggerProps): ReactElement {
  return (
    <MenuButton
      as="button"
      className={buttonClasses({
        className: ['inline-flex items-center gap-2', className].join(' ').trim(),
        variant: 'secondary',
      })}
      type="button"
    >
      <span>{children}</span>
      <ChevronDown aria-hidden="true" className="h-4 w-4" />
    </MenuButton>
  );
}

export function DropdownMenuItems({ children, align = 'end' }: DropdownMenuItemsProps): ReactElement {
  const alignmentClasses = align === 'end' ? 'right-0 origin-top-right' : 'left-0 origin-top-left';

  return (
    <Transition
      as={Fragment}
      enter="transition ease-out duration-100"
      enterFrom="transform opacity-0 scale-95"
      enterTo="transform opacity-100 scale-100"
      leave="transition ease-in duration-75"
      leaveFrom="transform opacity-100 scale-100"
      leaveTo="transform opacity-0 scale-95"
    >
      <MenuItems
        className={[
          'absolute z-50 mt-2 min-w-[220px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-1 shadow-lg focus:outline-none',
          alignmentClasses,
        ]
          .join(' ')
          .trim()}
      >
        {children}
      </MenuItems>
    </Transition>
  );
}

export function DropdownMenuItem({
  children,
  className = '',
  destructive = false,
  icon,
  ...props
}: DropdownMenuItemProps): ReactElement {
  return (
    <MenuItem disabled={props.disabled}>
      {({ active, disabled }) => (
        <button
          {...props}
          className={[
            'flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
            active ? 'bg-[var(--color-surface-muted)]' : '',
            destructive ? 'text-[var(--color-error)]' : 'text-[var(--color-text)]',
            disabled ? 'cursor-not-allowed opacity-50' : '',
            className,
          ]
            .join(' ')
            .trim()}
          disabled={disabled}
          type="button"
        >
          {icon ? <span className="mt-0.5 h-4 w-4 flex-shrink-0">{icon}</span> : null}
          <span className="min-w-0">{children}</span>
        </button>
      )}
    </MenuItem>
  );
}

export function DropdownMenuLinkItem({
  children,
  className = '',
  destructive = false,
  icon,
  ...props
}: DropdownMenuLinkItemProps): ReactElement {
  return (
    <MenuItem disabled={props['aria-disabled'] === true || props['aria-disabled'] === 'true'}>
      {({ active, disabled }) => (
        <a
          {...props}
          aria-disabled={disabled || props['aria-disabled']}
          className={[
            'flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
            active ? 'bg-[var(--color-surface-muted)]' : '',
            destructive ? 'text-[var(--color-error)]' : 'text-[var(--color-text)]',
            disabled ? 'pointer-events-none cursor-not-allowed opacity-50' : '',
            className,
          ]
            .join(' ')
            .trim()}
        >
          {icon ? <span className="mt-0.5 h-4 w-4 flex-shrink-0">{icon}</span> : null}
          <span className="min-w-0">{children}</span>
        </a>
      )}
    </MenuItem>
  );
}

export function DropdownMenuSeparator(): ReactElement {
  return <div aria-orientation="horizontal" className="my-1 border-t border-[var(--color-border)]" role="separator" />;
}

export default DropdownMenu;
