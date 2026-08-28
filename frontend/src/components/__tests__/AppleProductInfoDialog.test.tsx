/** @vitest-environment jsdom */
import '../../test/setup';
import '../../i18n';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import {
  AppleProductInfoCard,
  AppleProductInfoDialog,
} from '../AppleProductInfoDialog';

function renderDialog(onClose = vi.fn()): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <AppleProductInfoDialog onClose={onClose} open />
    </MemoryRouter>
  );
}

afterEach(async () => {
  cleanup();
  vi.restoreAllMocks();
  await i18n.changeLanguage('en');
});

describe('AppleProductInfoDialog', () => {
  it('renders the non-modal information Card with only the two safe destinations', () => {
    render(
      <MemoryRouter>
        <AppleProductInfoCard />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('heading', { level: 1, name: 'PulsePlate for Apple devices' })
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
      'href',
      '/bmi'
    );
    expect(
      screen.getByRole('link', { name: 'Learn about PulsePlate for Apple devices' })
    ).toHaveAttribute('href', '/marketing');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /buy|subscribe|upgrade|trial|restore/i })).not.toBeInTheDocument();
  });

  it('names the dialog, focuses free BMI first, and restores body scrolling on unmount', async () => {
    const previousOverflow = document.body.style.overflow;
    const rendered = renderDialog();

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

    rendered.unmount();
    expect(document.body.style.overflow).toBe(previousOverflow);
  });

  it('supports Escape, the top close action, and Not now without payment behavior', () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <MemoryRouter>
        <AppleProductInfoDialog onClose={onClose} open />
      </MemoryRouter>
    );

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Close information about PulsePlate for Apple devices',
      })
    );
    expect(onClose).toHaveBeenCalledTimes(2);

    fireEvent.click(screen.getByRole('button', { name: 'Not now' }));
    expect(onClose).toHaveBeenCalledTimes(3);

    rerender(
      <MemoryRouter>
        <AppleProductInfoDialog onClose={onClose} open={false} />
      </MemoryRouter>
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('cycles Tab and Shift+Tab within the dialog', () => {
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
    vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue(
      [rect] as unknown as DOMRectList
    );
    const offsetParentDescriptor = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'offsetParent'
    );
    Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
      configurable: true,
      get: () => document.body,
    });

    try {
      renderDialog();
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

  it('has no targeted accessibility violations', async () => {
    const { container } = renderDialog();

    expect(await axe(container)).toHaveNoViolations();
  });

  it.each([
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
      renderDialog();

      expect(screen.getByRole('dialog', { name: title })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: dismiss })).toBeInTheDocument();
      expect(screen.getByText(websiteFree)).toBeInTheDocument();
      expect(screen.getByText(noPurchases)).toBeInTheDocument();
    }
  );
});
