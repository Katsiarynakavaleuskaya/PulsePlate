/** @vitest-environment jsdom */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiHttpError, UnauthorizedError } from '../../../api/client';
import type {
  FitChefSupportHandoffResponse,
  FitChefSupportNeed,
} from '../../../api/fitchefSupportHandoff';
import { SettingsProvider } from '../../../lib/settings';
import Home from '../../../pages/Home';
import { SupportChoiceCard, type SupportChoiceRequester } from '../SupportChoiceCard';
import {
  fitChefSupportChoiceEventNames,
  fitChefSupportChoiceSensitiveFields,
  recordFitChefSupportChoiceEvent,
  setFitChefSupportChoiceEventSink,
  type FitChefSupportChoiceEvent,
} from '../supportChoiceEvents';

vi.mock('../../../lib/auth', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../../../lib/auth';

const BASE_EVENT_PAYLOAD = {
  surface: 'app',
  componentId: 'fitchef-support-choice',
  routePath: '/app',
} as const;

function validResponse(
  supportNeed: FitChefSupportNeed = 'daily_structure'
): FitChefSupportHandoffResponse {
  if (supportNeed === 'daily_structure') {
    return {
      schema_version: 'fitchef_support_handoff.v1',
      scenario: 'support_handoff',
      support_need: 'daily_structure',
      action: {
        action_type: 'handoff_to_product_surface',
        target_surface: 'pro_daily_plate',
      },
      user_confirmation_required: true,
      execution_authority: false,
      plan_mutation_authority: false,
      used_llm: false,
      wellness_boundary: 'wellness_planning_only',
    };
  }

  return {
    schema_version: 'fitchef_support_handoff.v1',
    scenario: 'support_handoff',
    support_need: 'weekly_structure',
    action: {
      action_type: 'handoff_to_product_surface',
      target_surface: 'pro_weekly_plan',
    },
    user_confirmation_required: true,
    execution_authority: false,
    plan_mutation_authority: false,
    used_llm: false,
    wellness_boundary: 'wellness_planning_only',
  };
}

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
} {
  let resolvePromise: (value: T) => void = () => undefined;
  let rejectPromise: (reason: unknown) => void = () => undefined;
  const promise = new Promise<T>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, resolve: resolvePromise, reject: rejectPromise };
}

function renderCard(
  requester: SupportChoiceRequester = vi.fn().mockResolvedValue(validResponse()),
  authState: 'authenticated' | 'unauthenticated' | 'unknown' = 'authenticated'
): ReturnType<typeof render> {
  return render(<SupportChoiceCard authState={authState} requester={requester} />);
}

describe('SupportChoiceCard', () => {
  const events: FitChefSupportChoiceEvent[] = [];

  beforeEach(() => {
    events.length = 0;
    setFitChefSupportChoiceEventSink((event) => events.push(event));
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
  });

  afterEach(() => {
    setFitChefSupportChoiceEventSink(null);
    cleanup();
    vi.restoreAllMocks();
  });

  it('emits viewed once per component instance under StrictMode', () => {
    render(
      <StrictMode>
        <SupportChoiceCard authState="authenticated" requester={vi.fn()} />
      </StrictMode>
    );

    expect(events.filter((event) => event.name === 'fitchef_support_choice_viewed')).toHaveLength(
      1
    );
  });

  it('renders exactly two native radios and submits only after the explicit CTA', async () => {
    const requester = vi.fn().mockResolvedValue(validResponse());
    const user = userEvent.setup();
    renderCard(requester);

    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(2);
    expect(screen.getByRole('radio', { name: /Help me structure today/i })).toHaveAttribute(
      'value',
      'daily_structure'
    );
    expect(screen.getByRole('radio', { name: /Help me structure my week/i })).toHaveAttribute(
      'value',
      'weekly_structure'
    );

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    expect(requester).not.toHaveBeenCalled();
    expect(events.some((event) => event.name === 'fitchef_support_need_selected')).toBe(false);

    await user.click(screen.getByRole('button', { name: 'Show my next step' }));

    await screen.findByText(/Based only on the option you selected/i);
    expect(requester).toHaveBeenCalledTimes(1);
    expect(requester).toHaveBeenCalledWith('daily_structure', {
      signal: expect.any(AbortSignal),
      onAuthError: expect.any(Function),
    });
    expect(events.map((event) => event.name)).toEqual([
      'fitchef_support_choice_viewed',
      'fitchef_support_need_selected',
      'fitchef_support_handoff_received',
    ]);
  });

  it('rejects selected-sink reentrant submit with admission set before controller creation', async () => {
    const pending = deferred<FitChefSupportHandoffResponse>();
    const requester = vi.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    const submit = screen.getByRole('button', { name: 'Show my next step' });
    let reenteredSelected = false;
    setFitChefSupportChoiceEventSink((event) => {
      events.push(event);
      if (event.name === 'fitchef_support_need_selected' && !reenteredSelected) {
        reenteredSelected = true;
        fireEvent.click(submit);
      }
    });

    fireEvent.click(submit);

    await waitFor(() => expect(requester).toHaveBeenCalledTimes(1));
    expect(
      events.filter((event) => event.name === 'fitchef_support_need_selected')
    ).toHaveLength(1);
    const admittedSignal = requester.mock.calls[0]?.[1]?.signal as AbortSignal;
    expect(admittedSignal.aborted).toBe(false);
    expect(screen.getByRole('button', { name: 'Loading next step…' })).toBeDisabled();
  });

  it.each(['dismiss', 'selection change'] as const)(
    'honors a synchronous selected-sink %s without calling the requester',
    async (reentrantAction) => {
      const requester = vi.fn();
      const abortSpy = vi.spyOn(AbortController.prototype, 'abort');
      const user = userEvent.setup();
      renderCard(requester);

      await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
      const submit = screen.getByRole('button', { name: 'Show my next step' });
      const dismiss = screen.getByRole('button', { name: 'Not now' });
      const weekly = screen.getByRole('radio', { name: /Help me structure my week/i });
      setFitChefSupportChoiceEventSink((event) => {
        events.push(event);
        if (event.name === 'fitchef_support_need_selected') {
          fireEvent.click(reentrantAction === 'dismiss' ? dismiss : weekly);
        }
      });

      fireEvent.click(submit);

      expect(requester).not.toHaveBeenCalled();
      expect(abortSpy).toHaveBeenCalledTimes(1);
      expect(
        events.filter((event) => event.name === 'fitchef_support_need_selected')
      ).toHaveLength(1);
      expect(events.filter((event) => event.name === 'fitchef_support_handoff_exited')).toEqual([
        {
          name: 'fitchef_support_handoff_exited',
          payload: {
            ...BASE_EVENT_PAYLOAD,
            outcome: reentrantAction === 'dismiss' ? 'dismissed' : 'changed_selection',
            supportNeed: 'daily_structure',
          },
        },
      ]);
      expect(screen.queryByRole('button', { name: 'Loading next step…' })).not.toBeInTheDocument();
      if (reentrantAction === 'dismiss') {
        expect(screen.getByText('Next-step pointer dismissed')).toBeVisible();
      } else {
        expect(weekly).toBeChecked();
        expect(screen.getByRole('button', { name: 'Show my next step' })).toBeEnabled();
      }
    }
  );

  it.each(['received', 'failure'] as const)(
    'keeps %s-sink submit reentrancy inside the admitted callback boundary',
    async (terminalCallback) => {
      const requester =
        terminalCallback === 'received'
          ? vi.fn().mockResolvedValue(validResponse())
          : vi.fn().mockRejectedValue(new ApiHttpError(500));
      const user = userEvent.setup();
      renderCard(requester);

      await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
      const submit = screen.getByRole('button', { name: 'Show my next step' });
      let reenteredTerminalCallback = false;
      setFitChefSupportChoiceEventSink((event) => {
        events.push(event);
        const isTargetCallback =
          (terminalCallback === 'received' &&
            event.name === 'fitchef_support_handoff_received') ||
          (terminalCallback === 'failure' &&
            event.name === 'fitchef_support_handoff_exited' &&
            event.payload.outcome === 'network_error');
        if (isTargetCallback && !reenteredTerminalCallback) {
          reenteredTerminalCallback = true;
          fireEvent.click(submit);
        }
      });

      fireEvent.click(submit);

      if (terminalCallback === 'received') {
        await screen.findByTestId('fitchef-support-result-copy');
      } else {
        await screen.findByText(/FitChef could not load a next-step pointer right now/);
      }
      expect(reenteredTerminalCallback).toBe(true);
      expect(requester).toHaveBeenCalledTimes(1);
      expect(
        events.filter((event) => event.name === 'fitchef_support_need_selected')
      ).toHaveLength(1);
      const admittedSignal = requester.mock.calls[0]?.[1]?.signal as AbortSignal;
      expect(admittedSignal.aborted).toBe(false);
    }
  );

  it('keeps the requester-supplied auth callback inline and inert', async () => {
    const authCallbackInvoked = vi.fn();
    const clearApiKey = vi.fn();
    const requester: SupportChoiceRequester = vi.fn(async (_supportNeed, options) => {
      options?.onAuthError?.(403, { clearApiKey });
      authCallbackInvoked();
      return validResponse();
    });
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));

    await screen.findByTestId('fitchef-support-result-copy');
    expect(authCallbackInvoked).toHaveBeenCalledTimes(1);
    expect(clearApiKey).not.toHaveBeenCalled();
  });

  it('preserves native keyboard selection and visible focus without requesting data', async () => {
    const requester = vi.fn();
    const user = userEvent.setup();
    renderCard(requester);

    const daily = screen.getByRole('radio', { name: /Help me structure today/i });
    const weekly = screen.getByRole('radio', { name: /Help me structure my week/i });
    daily.focus();
    expect(daily).toHaveFocus();
    expect(daily).toHaveClass('focus:ring-[var(--color-primary)]');

    await user.keyboard('{ArrowRight}');

    expect(weekly).toBeChecked();
    expect(requester).not.toHaveBeenCalled();
  });

  it('blocks submit while session state is unknown', async () => {
    const requester = vi.fn();
    const user = userEvent.setup();
    renderCard(requester, 'unknown');

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));

    expect(screen.getByText('Checking session before this request can be sent.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Show my next step' })).toBeDisabled();
    expect(requester).not.toHaveBeenCalled();
  });

  it('keeps known unauthenticated access inline without requesting or emitting flow events', async () => {
    const requester = vi.fn();
    const user = userEvent.setup();
    renderCard(requester, 'unauthenticated');

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));

    expect(
      screen.getByText(
        'PulsePlate could not confirm access for this session. Nothing has been opened or run. No plan has been created or changed. Sign in or check your account access, then try again.'
      )
    ).toBeVisible();
    const submit = screen.getByRole('button', { name: 'Show my next step' });
    expect(submit).toBeDisabled();
    await user.click(submit);
    expect(requester).not.toHaveBeenCalled();
    expect(events.map((event) => event.name)).toEqual(['fitchef_support_choice_viewed']);
    expect(events.some((event) => event.name === 'fitchef_support_need_selected')).toBe(false);
    expect(events.some((event) => event.name === 'fitchef_support_handoff_exited')).toBe(false);
    expect(within(screen.getByTestId('fitchef-support-choice')).queryAllByRole('link')).toEqual([]);
  });

  it.each(['idle', 'ready'] as const)(
    'dismisses from %s without emitting an exit before accepted submit',
    async (startingState) => {
      const requester = vi.fn();
      const user = userEvent.setup();
      renderCard(requester);
      if (startingState === 'ready') {
        await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
      }

      await user.click(screen.getByRole('button', { name: 'Not now' }));

      expect(screen.getByText('Next-step pointer dismissed')).toBeVisible();
      expect(requester).not.toHaveBeenCalled();
      expect(
        events.filter((event) => event.name === 'fitchef_support_handoff_exited')
      ).toHaveLength(0);
    }
  );

  it.each([401, 403] as const)(
    'keeps a stale authenticated HTTP %s failure inline without redirecting',
    async (status) => {
      const clearApiKey = vi.fn();
      const pathnameBefore = window.location.pathname;
      const requester: SupportChoiceRequester = vi.fn(async (_supportNeed, options) => {
        options?.onAuthError?.(status, { clearApiKey });
        throw new UnauthorizedError(`raw stale auth ${status}`);
      });
      const user = userEvent.setup();
      renderCard(requester, 'authenticated');

      await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
      await user.click(screen.getByRole('button', { name: 'Show my next step' }));

      expect(
        await screen.findByText(/FitChef could not verify access for this request/)
      ).toHaveTextContent('No plan has been created or changed.');
      expect(screen.queryByText(new RegExp(`raw stale auth ${status}`))).not.toBeInTheDocument();
      expect(clearApiKey).not.toHaveBeenCalled();
      expect(window.location.pathname).toBe(pathnameBefore);
      expect(events).toEqual(
        expect.arrayContaining([
          {
            name: 'fitchef_support_handoff_exited',
            payload: {
              ...BASE_EVENT_PAYLOAD,
              outcome: 'auth_error',
              supportNeed: 'daily_structure',
            },
          },
        ])
      );
      expect(within(screen.getByTestId('fitchef-support-choice')).queryAllByRole('link')).toEqual(
        []
      );
    }
  );

  it('aborts a pending request on selection change and ignores its late response', async () => {
    const pending = deferred<FitChefSupportHandoffResponse>();
    const requester = vi.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));

    const pendingButton = screen.getByRole('button', { name: 'Loading next step…' });
    expect(pendingButton).toBeDisabled();
    await user.click(pendingButton);
    expect(requester).toHaveBeenCalledTimes(1);
    const signal = requester.mock.calls[0]?.[1]?.signal as AbortSignal;

    await user.click(screen.getByRole('radio', { name: /Help me structure my week/i }));

    expect(signal.aborted).toBe(true);
    expect(screen.getByRole('button', { name: 'Show my next step' })).toBeEnabled();
    expect(requester).toHaveBeenCalledTimes(1);

    await act(async () => {
      pending.resolve(validResponse('daily_structure'));
      await pending.promise;
    });

    expect(screen.queryByTestId('fitchef-support-result-copy')).not.toBeInTheDocument();
    expect(
      events.filter(
        (event) =>
          event.name === 'fitchef_support_handoff_exited' &&
          event.payload.outcome === 'changed_selection'
      )
    ).toHaveLength(1);
    expect(events.some((event) => event.name === 'fitchef_support_handoff_received')).toBe(false);
  });

  it('dismisses a pending submitted lifecycle once and aborts the request', async () => {
    const pending = deferred<FitChefSupportHandoffResponse>();
    const requester = vi.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    const signal = requester.mock.calls[0]?.[1]?.signal as AbortSignal;
    const dismiss = screen.getByRole('button', { name: 'Not now' });
    let reenteredDismiss = false;
    setFitChefSupportChoiceEventSink((event) => {
      events.push(event);
      if (
        event.name === 'fitchef_support_handoff_exited' &&
        event.payload.outcome === 'dismissed' &&
        !reenteredDismiss
      ) {
        reenteredDismiss = true;
        fireEvent.click(dismiss);
      }
    });

    fireEvent.click(dismiss);

    expect(signal.aborted).toBe(true);
    expect(screen.getByText('Next-step pointer dismissed')).toBeVisible();
    expect(events.filter((event) => event.name === 'fitchef_support_handoff_exited')).toEqual([
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          supportNeed: 'daily_structure',
        },
      },
    ]);
  });

  it('aborts on unmount and keeps AbortError silent', async () => {
    const pending = deferred<FitChefSupportHandoffResponse>();
    const requester = vi.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();
    const rendered = renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    const signal = requester.mock.calls[0]?.[1]?.signal as AbortSignal;

    rendered.unmount();
    expect(signal.aborted).toBe(true);

    await act(async () => {
      pending.reject(new DOMException('aborted', 'AbortError'));
      await Promise.resolve();
    });

    expect(events.some((event) => event.name === 'fitchef_support_handoff_exited')).toBe(false);
  });

  it('keeps an object-shaped AbortError silent', async () => {
    const requester = vi.fn().mockRejectedValue({ name: 'AbortError' });
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    await waitFor(() => expect(requester).toHaveBeenCalledTimes(1));

    expect(screen.queryByText('Next-step pointer unavailable')).not.toBeInTheDocument();
    expect(events.some((event) => event.name === 'fitchef_support_handoff_exited')).toBe(false);
  });

  it.each([
    [
      'auth_error',
      new UnauthorizedError('raw auth detail'),
      'FitChef could not verify access for this request.',
    ],
    [
      'validation_error',
      new ApiHttpError(422),
      'PulsePlate could not validate this support pointer. Nothing has been opened or run. No plan has been created or changed. Choose an option and try again.',
    ],
    [
      'feature_unavailable',
      new ApiHttpError(503),
      'FitChef’s next-step pointer is unavailable right now.',
    ],
    [
      'network_error',
      new ApiHttpError(500),
      'FitChef could not load a next-step pointer right now.',
    ],
  ] as const)(
    'renders fixed %s copy, focuses retry, and can recover',
    async (outcome, failure, expectedCopy) => {
      const requester = vi
        .fn()
        .mockRejectedValueOnce(failure)
        .mockResolvedValueOnce(validResponse());
      const user = userEvent.setup();
      renderCard(requester);

      await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
      await user.click(screen.getByRole('button', { name: 'Show my next step' }));

      const renderedError =
        outcome === 'validation_error'
          ? await screen.findByText(expectedCopy, { exact: true })
          : await screen.findByText(new RegExp(expectedCopy));
      if (outcome === 'validation_error') {
        expect(renderedError.textContent).toBe(expectedCopy);
        expect(renderedError.textContent ?? '').not.toMatch(/\bsafe\b/i);
      } else {
        expect(renderedError).toHaveTextContent('No plan has been created or changed.');
      }
      expect(screen.queryByText(/raw auth detail/i)).not.toBeInTheDocument();
      const retry = screen.getByRole('button', { name: 'Try again' });
      await waitFor(() => expect(retry).toHaveFocus());
      expect(events).toEqual(
        expect.arrayContaining([
          {
            name: 'fitchef_support_handoff_exited',
            payload: {
              ...BASE_EVENT_PAYLOAD,
              outcome,
              supportNeed: 'daily_structure',
            },
          },
        ])
      );

      await user.click(retry);
      expect(await screen.findByTestId('fitchef-support-result-copy')).toHaveTextContent(
        'No plan has been created or changed.'
      );
      expect(requester).toHaveBeenCalledTimes(2);
    }
  );

  it.each(['selection change', 'dismiss'] as const)(
    'keeps one failure exit when error is followed by %s',
    async (followUp) => {
      const requester = vi.fn().mockRejectedValue(new ApiHttpError(500));
      const user = userEvent.setup();
      renderCard(requester);

      await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
      await user.click(screen.getByRole('button', { name: 'Show my next step' }));
      await screen.findByText(/FitChef could not load a next-step pointer right now/);

      if (followUp === 'selection change') {
        await user.click(screen.getByRole('radio', { name: /Help me structure my week/i }));
        expect(screen.getByRole('button', { name: 'Show my next step' })).toBeEnabled();
      } else {
        await user.click(screen.getByRole('button', { name: 'Not now' }));
        expect(screen.getByText('Next-step pointer dismissed')).toBeVisible();
      }

      expect(events.filter((event) => event.name === 'fitchef_support_handoff_exited')).toEqual([
        {
          name: 'fitchef_support_handoff_exited',
          payload: {
            ...BASE_EVENT_PAYLOAD,
            outcome: 'network_error',
            supportNeed: 'daily_structure',
          },
        },
      ]);
    }
  );

  it('uses the submit-time auth snapshot and records confirmation exactly once', async () => {
    const pending = deferred<FitChefSupportHandoffResponse>();
    const requester = vi.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();
    const rendered = renderCard(requester, 'authenticated');

    await user.click(screen.getByRole('radio', { name: /Help me structure my week/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    rendered.rerender(<SupportChoiceCard authState="unauthenticated" requester={requester} />);

    await act(async () => {
      pending.resolve(validResponse('weekly_structure'));
      await pending.promise;
    });

    const confirm = await screen.findByRole('button', {
      name: 'I understand this next step',
    });
    let reenteredConfirmation = false;
    setFitChefSupportChoiceEventSink((event) => {
      events.push(event);
      if (event.name === 'fitchef_support_handoff_confirmed' && !reenteredConfirmation) {
        reenteredConfirmation = true;
        fireEvent.click(confirm);
      }
    });
    fireEvent.click(confirm);

    expect(screen.getByTestId('fitchef-support-confirmed-copy')).toHaveTextContent(
      'Next-step pointer acknowledged. Nothing has been opened or run. No plan has been created or changed.'
    );
    expect(events.filter((event) => event.name === 'fitchef_support_handoff_confirmed')).toEqual([
      {
        name: 'fitchef_support_handoff_confirmed',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_weekly_plan',
          authState: 'authenticated',
        },
      },
    ]);
    expect(events.find((event) => event.name === 'fitchef_support_handoff_received')).toMatchObject(
      { payload: { authState: 'authenticated' } }
    );
  });

  it('resets confirmation on a new selection without auto-submitting', async () => {
    const requester = vi.fn().mockResolvedValue(validResponse());
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    await user.click(await screen.findByRole('button', { name: 'I understand this next step' }));
    await user.click(screen.getByRole('radio', { name: /Help me structure my week/i }));

    expect(screen.queryByTestId('fitchef-support-confirmed-copy')).not.toBeInTheDocument();
    expect(screen.queryByTestId('fitchef-support-result-copy')).not.toBeInTheDocument();
    expect(requester).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Show my next step' })).toBeEnabled();
  });

  it('dismisses a confirmed submitted lifecycle once with its validated target', async () => {
    const requester = vi.fn().mockResolvedValue(validResponse('weekly_structure'));
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure my week/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    await user.click(
      await screen.findByRole('button', { name: 'I understand this next step' })
    );
    await user.click(screen.getByRole('button', { name: 'Not now' }));

    expect(events.filter((event) => event.name === 'fitchef_support_handoff_exited')).toEqual([
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_weekly_plan',
        },
      },
    ]);
  });

  it('dismisses explicitly, resets the local flow, and creates no interactive target', async () => {
    const storageSpy = vi.spyOn(Storage.prototype, 'setItem');
    const requester = vi.fn().mockResolvedValue(validResponse());
    const user = userEvent.setup();
    renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    const target = await screen.findByTestId('fitchef-support-target-label');
    expect(target.closest('a, button')).toBeNull();
    expect(within(screen.getByTestId('fitchef-support-choice')).queryAllByRole('link')).toEqual([]);

    await user.click(screen.getByRole('button', { name: 'Not now' }));

    expect(screen.getByText('Next-step pointer dismissed')).toBeVisible();
    screen.getAllByRole('radio').forEach((radio) => expect(radio).not.toBeChecked());
    expect(storageSpy).not.toHaveBeenCalled();
    expect(events.filter((event) => event.name === 'fitchef_support_handoff_exited')).toEqual([
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          supportNeed: 'daily_structure',
          targetSurface: 'pro_daily_plate',
        },
      },
    ]);
  });

  it('passes targeted axe checks in the complete success state', async () => {
    const requester = vi.fn().mockResolvedValue(validResponse());
    const user = userEvent.setup();
    const { container } = renderCard(requester);

    await user.click(screen.getByRole('radio', { name: /Help me structure today/i }));
    await user.click(screen.getByRole('button', { name: 'Show my next step' }));
    await screen.findByTestId('fitchef-support-result-copy');

    expect(await axe(container)).toHaveNoViolations();
  });

  it('mounts once after planning preview and before the tier rail without replacing Home CTAs', () => {
    render(
      <SettingsProvider>
        <MemoryRouter>
          <Home />
        </MemoryRouter>
      </SettingsProvider>
    );

    const supportCards = screen.getAllByTestId('fitchef-support-choice');
    const planningPreview = screen.getByTestId('planning-preview-card');
    const tierRail = screen.getByTestId('tier-value-rail');
    expect(supportCards).toHaveLength(1);
    expect(
      planningPreview.compareDocumentPosition(supportCards[0]) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(
      supportCards[0].compareDocumentPosition(tierRail) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Continue planning' })).toBeVisible();
    expect(screen.getByRole('link', { name: /Continue into the plate flow/i })).toBeVisible();
    expect(screen.getByRole('link', { name: /Use progress check-ins/i })).toBeVisible();
    expect(screen.getByRole('link', { name: /Unlock weekly planning/i })).toBeVisible();
  });
});

describe('FitChef support choice local event contract', () => {
  afterEach(() => {
    setFitChefSupportChoiceEventSink(null);
    vi.restoreAllMocks();
  });

  it('keeps the exact five-name event universe', () => {
    expect(fitChefSupportChoiceEventNames).toEqual([
      'fitchef_support_choice_viewed',
      'fitchef_support_need_selected',
      'fitchef_support_handoff_received',
      'fitchef_support_handoff_confirmed',
      'fitchef_support_handoff_exited',
    ]);
  });

  it('keeps accepted submits per view classified as an unbounded frequency', () => {
    const funnel = readFileSync(
      resolve(process.cwd(), '../docs/analytics/FITCHEF_SUPPORT_CHOICE_FUNNEL.md'),
      'utf8'
    );

    expect(funnel).toContain(
      'accepted_submits_per_view = fitchef_support_need_selected / fitchef_support_choice_viewed'
    );
    expect(funnel).not.toContain('selection_rate =');
    expect(funnel).toMatch(/frequency, not a probability or bounded rate,[\s\S]*may exceed `1`/);
    expect(funnel).toContain(
      'terminal_exit_rate = fitchef_support_handoff_exited / fitchef_support_need_selected'
    );
  });

  it('accepts each event-specific schema and rejects unknown, extra, and sensitive fields', () => {
    const localEvents: FitChefSupportChoiceEvent[] = [];
    setFitChefSupportChoiceEventSink((event) => localEvents.push(event));

    const candidates: FitChefSupportChoiceEvent[] = [
      { name: 'fitchef_support_choice_viewed', payload: BASE_EVENT_PAYLOAD },
      {
        name: 'fitchef_support_need_selected',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          targetSurface: 'pro_daily_plate',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_confirmed',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_weekly_plan',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'changed_selection',
          supportNeed: 'weekly_structure',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          supportNeed: 'daily_structure',
          targetSurface: 'pro_daily_plate',
        },
      },
    ];

    candidates.forEach((candidate) => {
      expect(recordFitChefSupportChoiceEvent(candidate)).toBe(true);
    });
    expect(localEvents).toEqual(candidates);

    const invalidCandidates: unknown[] = [
      null,
      { name: 42, payload: BASE_EVENT_PAYLOAD },
      { name: 'fitchef_support_choice_viewed', payload: 'not-an-object' },
      {
        name: 'fitchef_support_choice_viewed',
        payload: { ...BASE_EVENT_PAYLOAD, surface: 'other' },
      },
      {
        name: 'fitchef_support_choice_viewed',
        payload: { ...BASE_EVENT_PAYLOAD, componentId: 'other' },
      },
      {
        name: 'fitchef_support_choice_viewed',
        payload: { ...BASE_EVENT_PAYLOAD, routePath: '/other' },
      },
      {
        name: 'fitchef_support_choice_viewed',
        payload: { ...BASE_EVENT_PAYLOAD, freeText: 'never emit this' },
      },
      {
        name: 'fitchef_support_need_selected',
        payload: { ...BASE_EVENT_PAYLOAD, authState: 'authenticated' },
      },
      {
        name: 'fitchef_support_need_selected',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'inferred_need',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_need_selected',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          authState: 'maybe',
        },
      },
      {
        name: 'fitchef_support_need_selected',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          authState: 'unauthenticated',
        },
      },
      {
        name: 'fitchef_support_need_selected',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          authState: 'unknown',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'inferred_need',
          targetSurface: 'pro_daily_plate',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          targetSurface: '/plate',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          targetSurface: 'pro_weekly_plan',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_daily_plate',
          authState: 'authenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          targetSurface: 'pro_daily_plate',
          authState: 'unauthenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_weekly_plan',
          authState: 'unknown',
        },
      },
      {
        name: 'fitchef_support_handoff_confirmed',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_weekly_plan',
          authState: 'maybe',
        },
      },
      {
        name: 'fitchef_support_handoff_confirmed',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'daily_structure',
          targetSurface: 'pro_daily_plate',
          authState: 'unauthenticated',
        },
      },
      {
        name: 'fitchef_support_handoff_confirmed',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_weekly_plan',
          authState: 'unknown',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: { ...BASE_EVENT_PAYLOAD, outcome: 'unknown_outcome' },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: { ...BASE_EVENT_PAYLOAD, outcome: 'dismissed' },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          targetSurface: 'pro_daily_plate',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'network_error',
          supportNeed: 'inferred_need',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          supportNeed: 'daily_structure',
          targetSurface: '/plate',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          outcome: 'dismissed',
          supportNeed: 'weekly_structure',
          targetSurface: 'pro_daily_plate',
        },
      },
      {
        name: 'fitchef_support_handoff_exited',
        payload: { ...BASE_EVENT_PAYLOAD, surface: 'other', outcome: 'dismissed' },
      },
      {
        name: 'fitchef_support_unknown',
        payload: BASE_EVENT_PAYLOAD,
      },
    ];

    invalidCandidates.forEach((candidate) => {
      expect(recordFitChefSupportChoiceEvent(candidate)).toBe(false);
    });
    expect(fitChefSupportChoiceSensitiveFields).toContain('rawError');
    expect(fitChefSupportChoiceSensitiveFields).toContain('nutritionTargets');
    expect(localEvents).toHaveLength(candidates.length);
  });

  it('rejects non-plain event records and accepts exact null-prototype records', () => {
    const localEvents: FitChefSupportChoiceEvent[] = [];
    setFitChefSupportChoiceEventSink((event) => localEvents.push(event));
    const nonPlainEvent = Object.assign(Object.create({ inherited: true }), {
      name: 'fitchef_support_choice_viewed',
      payload: BASE_EVENT_PAYLOAD,
    });
    const nonPlainPayload = {
      name: 'fitchef_support_choice_viewed',
      payload: Object.assign(Object.create({ inherited: true }), BASE_EVENT_PAYLOAD),
    };

    expect(recordFitChefSupportChoiceEvent(nonPlainEvent)).toBe(false);
    expect(recordFitChefSupportChoiceEvent(nonPlainPayload)).toBe(false);

    const nullPrototypeEvent = Object.assign(Object.create(null), {
      name: 'fitchef_support_choice_viewed',
      payload: Object.assign(Object.create(null), BASE_EVENT_PAYLOAD),
    });
    Object.defineProperty(nullPrototypeEvent.payload, 'hidden', {
      enumerable: false,
      value: 'ignored because the contract is own-enumerable keys',
    });

    expect(recordFitChefSupportChoiceEvent(nullPrototypeEvent)).toBe(true);
    expect(localEvents).toEqual([
      { name: 'fitchef_support_choice_viewed', payload: BASE_EVENT_PAYLOAD },
    ]);
  });

  it('swallows sink failures and uses no network, beacon, storage, or cookie transport', () => {
    const fetchSpy = vi.fn();
    const beaconSpy = vi.fn();
    const storageSpy = vi.spyOn(Storage.prototype, 'setItem');
    const cookieBefore = document.cookie;
    vi.stubGlobal('fetch', fetchSpy);
    Object.defineProperty(navigator, 'sendBeacon', {
      configurable: true,
      value: beaconSpy,
    });
    setFitChefSupportChoiceEventSink(() => {
      throw new Error('local sink failed');
    });

    expect(
      recordFitChefSupportChoiceEvent({
        name: 'fitchef_support_choice_viewed',
        payload: BASE_EVENT_PAYLOAD,
      })
    ).toBe(true);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(beaconSpy).not.toHaveBeenCalled();
    expect(storageSpy).not.toHaveBeenCalled();
    expect(document.cookie).toBe(cookieBefore);
  });
});
