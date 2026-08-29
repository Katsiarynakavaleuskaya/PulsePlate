/** @vitest-environment jsdom */
import '../../test/setup';
import '../../i18n';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, test, vi } from 'vitest';
import i18n from '../../i18n';
import { AppleProductInfoDialog } from '../AppleProductInfoDialog';
import PremiumGate from '../PremiumGate';

function renderWithRouter(element: JSX.Element): ReturnType<typeof render> {
  return render(<MemoryRouter>{element}</MemoryRouter>);
}

afterEach(async () => {
  cleanup();
  vi.restoreAllMocks();
  document.body.style.overflow = '';
  await i18n.changeLanguage('en');
});

describe('PremiumGate', () => {
  test('shows children directly when premium', () => {
    render(
      <PremiumGate isPremium>
        <div data-testid="content">Premium content</div>
      </PremiumGate>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('keeps the preview inert and opens the shared information dialog', async () => {
    renderWithRouter(
      <PremiumGate isPremium={false}>
        <button data-testid="content" type="button">
          Gated content
        </button>
      </PremiumGate>
    );

    const preview = screen.getByTestId('content').parentElement;
    expect(preview?.hasAttribute('inert') || preview?.getAttribute('aria-hidden') === 'true').toBe(
      true
    );

    const trigger = screen.getByRole('button', {
      name: 'Learn about PulsePlate for Apple devices',
    });
    expect(trigger).toHaveAttribute('aria-haspopup', 'dialog');
    expect(trigger).toHaveClass(
      'border-[var(--color-border)]',
      'bg-[var(--color-bg)]',
      'text-[var(--color-text)]'
    );
    expect(trigger).not.toHaveClass(
      'bg-[var(--color-primary)]',
      'text-[var(--color-primary-foreground)]'
    );
    fireEvent.click(trigger);

    const dialog = screen.getByRole('dialog', { name: 'PulsePlate for Apple devices' });
    expect(dialog).toBeInTheDocument();
    const descriptionId = dialog.getAttribute('aria-describedby');
    expect(descriptionId).toBeTruthy();
    expect(document.getElementById(descriptionId ?? '')).toHaveTextContent(
      'This website is free to use.'
    );
    expect(document.getElementById(descriptionId ?? '')).toHaveTextContent(
      'Purchases are not offered on this website.'
    );
    expect(document.body.style.overflow).toBe('hidden');
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveFocus();
    });
    expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
      'href',
      '/bmi'
    );
    expect(
      screen.getByRole('link', { name: 'Learn about PulsePlate for Apple devices' })
    ).toHaveAttribute('href', '/marketing');
    expect(
      screen.queryByRole('button', { name: /buy|subscribe|upgrade|trial|restore/i })
    ).not.toBeInTheDocument();
  });

  test('restores trigger focus after Escape, top close, and Not now', async () => {
    renderWithRouter(
      <PremiumGate isPremium={false}>
        <div>Gated content</div>
      </PremiumGate>
    );

    const trigger = screen.getByRole('button', {
      name: 'Learn about PulsePlate for Apple devices',
    });
    fireEvent.click(trigger);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

    await waitFor(() => expect(trigger).toHaveFocus());
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(trigger);
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Close information about PulsePlate for Apple devices',
      })
    );
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole('button', { name: 'Not now' }));
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe('');
  });

  test('restores the previous body scroll state when the open gate unmounts', async () => {
    const previousOverflow = 'scroll';
    document.body.style.overflow = previousOverflow;
    const rendered = renderWithRouter(
      <PremiumGate isPremium={false}>
        <div>Gated content</div>
      </PremiumGate>
    );

    fireEvent.click(
      screen.getByRole('button', { name: 'Learn about PulsePlate for Apple devices' })
    );
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveFocus();
    });

    rendered.unmount();
    expect(document.body.style.overflow).toBe(previousOverflow);
  });

  test('renders no dialog when the shared information boundary is closed', () => {
    renderWithRouter(<AppleProductInfoDialog onClose={vi.fn()} open={false} />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('cycles Tab and Shift+Tab within the information dialog', () => {
    const rect = {
      bottom: 44,
      height: 44,
      left: 0,
      right: 100,
      top: 0,
      width: 100,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect;
    vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue([
      rect,
    ] as unknown as DOMRectList);
    const offsetParentDescriptor = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'offsetParent'
    );
    Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
      configurable: true,
      get: () => document.body,
    });

    try {
      renderWithRouter(
        <PremiumGate isPremium={false}>
          <div>Gated content</div>
        </PremiumGate>
      );
      fireEvent.click(
        screen.getByRole('button', { name: 'Learn about PulsePlate for Apple devices' })
      );

      const dialog = screen.getByRole('dialog');
      const close = screen.getByRole('button', {
        name: 'Close information about PulsePlate for Apple devices',
      });
      const notNow = screen.getByRole('button', { name: 'Not now' });

      notNow.focus();
      fireEvent.keyDown(dialog, { key: 'Tab' });
      expect(close).toHaveFocus();

      close.focus();
      fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
      expect(notNow).toHaveFocus();
    } finally {
      if (offsetParentDescriptor) {
        Object.defineProperty(HTMLElement.prototype, 'offsetParent', offsetParentDescriptor);
      } else {
        Reflect.deleteProperty(HTMLElement.prototype, 'offsetParent');
      }
    }
  });

  test('has no targeted accessibility violations in the open dialog state', async () => {
    const { container } = renderWithRouter(
      <PremiumGate isPremium={false}>
        <div>Gated content</div>
      </PremiumGate>
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Learn about PulsePlate for Apple devices' })
    );

    expect(await axe(container)).toHaveNoViolations();
  });

  test('accepts old source metadata without giving it visible or action authority', () => {
    renderWithRouter(
      <PremiumGate
        isPremium={false}
        paywallSource="pro_daily_plate"
        source="plate_page"
        triggerReason="upgrade_for_export"
      >
        <div>Gated content</div>
      </PremiumGate>
    );

    fireEvent.click(
      screen.getByRole('button', { name: 'Learn about PulsePlate for Apple devices' })
    );
    expect(document.body).not.toHaveTextContent(/plate_page|pro_daily_plate|upgrade_for_export/i);
    expect(
      screen.queryByRole('button', { name: /buy|upgrade|subscribe|trial|restore/i })
    ).not.toBeInTheDocument();
  });

  test.each([
    [
      'ru',
      'PulsePlate для устройств Apple',
      'Не сейчас',
      'Этим сайтом можно пользоваться бесплатно.',
      'На этом сайте мы не предлагаем покупки.',
    ],
    [
      'es',
      'PulsePlate para dispositivos Apple',
      'Ahora no',
      'Este sitio web es gratuito.',
      'No ofrecemos compras en este sitio web.',
    ],
  ])(
    'keeps the information boundary localized in %s',
    async (language, title, dismiss, websiteFree, noPurchases) => {
      await i18n.changeLanguage(language);
      renderWithRouter(
        <PremiumGate isPremium={false}>
          <div>Gated content</div>
        </PremiumGate>
      );

      fireEvent.click(screen.getByRole('button', { name: i18n.t('appleProduct.learnMore') }));

      expect(screen.getByRole('dialog', { name: title })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: dismiss })).toBeInTheDocument();
      expect(screen.getByText(websiteFree)).toBeInTheDocument();
      expect(screen.getByText(noPurchases)).toBeInTheDocument();
    }
  );
});
