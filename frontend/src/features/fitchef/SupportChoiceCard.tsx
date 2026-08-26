import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, ReactElement } from 'react';
import {
  FitChefSupportHandoffValidationError,
  requestFitChefSupportHandoff,
  type FitChefSupportHandoffRequestOptions,
  type FitChefSupportHandoffResponse,
  type FitChefSupportNeed,
  type FitChefSupportTargetSurface,
} from '../../api/fitchefSupportHandoff';
import { ApiHttpError, UnauthorizedError } from '../../api/client';
import {
  Alert,
  Button,
  Card,
  CardContent,
  RadioGroup,
  RadioGroupOption,
} from '../../components/ui';
import {
  trackFitChefSupportChoiceEvent,
  type FitChefSupportAuthState,
  type FitChefSupportExitOutcome,
} from './supportChoiceEvents';

export type SupportChoiceRequester = (
  supportNeed: FitChefSupportNeed,
  options?: FitChefSupportHandoffRequestOptions
) => Promise<FitChefSupportHandoffResponse>;

export type SupportChoiceViewState =
  | {
      status: 'idle' | 'dismissed';
      selectedNeed: null;
      result: null;
      errorCategory: null;
    }
  | {
      status: 'ready' | 'pending';
      selectedNeed: FitChefSupportNeed;
      result: null;
      errorCategory: null;
    }
  | {
      status: 'success' | 'confirmed';
      selectedNeed: FitChefSupportNeed;
      result: FitChefSupportHandoffResponse;
      errorCategory: null;
    }
  | {
      status: 'error';
      selectedNeed: FitChefSupportNeed;
      result: null;
      errorCategory: Exclude<FitChefSupportExitOutcome, 'dismissed' | 'changed_selection'>;
    };

interface SupportChoiceCardProps {
  authState: FitChefSupportAuthState;
  requester?: SupportChoiceRequester;
}

interface SupportChoiceCardViewProps {
  authState: FitChefSupportAuthState;
  state: SupportChoiceViewState;
  onSelect: (supportNeed: FitChefSupportNeed) => void;
  onSubmit: () => void;
  onConfirm: () => void;
  onDismiss: () => void;
}

interface SubmittedSupportLifecycle {
  supportNeed: FitChefSupportNeed;
  targetSurface?: FitChefSupportTargetSurface;
  terminated: boolean;
}

const INTRO_COPY =
  'Choose whether you want a pointer for today or for the week. FitChef uses only the option you select; it does not inspect or create a plan.';

const RESULT_COPY: Record<FitChefSupportTargetSurface, string> = {
  pro_daily_plate:
    'Based only on the option you selected, FitChef can point to the Daily plate product area. Nothing has been opened or run. No plan has been created or changed.',
  pro_weekly_plan:
    'Based only on the option you selected, FitChef can point to the Weekly planning product area. Nothing has been opened or run. No plan has been created or changed.',
};

const TARGET_LABELS: Record<FitChefSupportTargetSurface, string> = {
  pro_daily_plate: 'Daily plate product area',
  pro_weekly_plan: 'Weekly planning product area',
};

const ERROR_COPY: Record<
  Exclude<FitChefSupportExitOutcome, 'dismissed' | 'changed_selection'>,
  string
> = {
  auth_error:
    'FitChef could not verify access for this request. Nothing has been opened or run. No plan has been created or changed.',
  validation_error:
    'PulsePlate could not validate this support pointer. Nothing has been opened or run. No plan has been created or changed. Choose an option and try again.',
  feature_unavailable:
    'FitChef’s next-step pointer is unavailable right now. Nothing has been opened or run. No plan has been created or changed.',
  network_error:
    'FitChef could not load a next-step pointer right now. Nothing has been opened or run. No plan has been created or changed.',
};

const CONFIRMED_COPY =
  'Next-step pointer acknowledged. Nothing has been opened or run. No plan has been created or changed.';

const UNAUTHENTICATED_COPY =
  'PulsePlate could not confirm access for this session. Nothing has been opened or run. No plan has been created or changed. Sign in or check your account access, then try again.';

const BASE_EVENT_PAYLOAD = {
  surface: 'app',
  componentId: 'fitchef-support-choice',
  routePath: '/app',
} as const;

function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === 'AbortError') ||
    (error !== null && typeof error === 'object' && 'name' in error && error.name === 'AbortError')
  );
}

function classifyError(
  error: unknown
): Exclude<FitChefSupportExitOutcome, 'dismissed' | 'changed_selection'> {
  if (
    error instanceof UnauthorizedError ||
    (error instanceof ApiHttpError && (error.status === 401 || error.status === 403))
  ) {
    return 'auth_error';
  }
  if (
    error instanceof FitChefSupportHandoffValidationError ||
    error instanceof SyntaxError ||
    (error instanceof ApiHttpError && error.status === 422)
  ) {
    return 'validation_error';
  }
  if (error instanceof ApiHttpError && error.status === 503) {
    return 'feature_unavailable';
  }
  return 'network_error';
}

export function SupportChoiceCardView({
  authState,
  state,
  onSelect,
  onSubmit,
  onConfirm,
  onDismiss,
}: SupportChoiceCardViewProps): ReactElement {
  const selectedNeed = state.selectedNeed;
  const isPending = state.status === 'pending';
  const canSubmit =
    selectedNeed !== null &&
    authState === 'authenticated' &&
    (state.status === 'ready' || state.status === 'error');
  const submitLabel = state.status === 'error' ? 'Try again' : 'Show my next step';

  return (
    <Card
      className="rounded-[2rem] border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] shadow-[var(--shadow-lg)]"
      data-testid="fitchef-support-choice"
    >
      <CardContent className="space-y-5 p-5 sm:p-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
            FitChef support choice
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[var(--color-text)]">
            Choose the scope of your next-step pointer
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{INTRO_COPY}</p>
        </div>

        <RadioGroup legend="What would you like help structuring?" orientation="horizontal">
          <RadioGroupOption
            checked={selectedNeed === 'daily_structure'}
            description="Request one bounded pointer for today."
            label="Help me structure today"
            name="fitchef-support-need"
            value="daily_structure"
            onChange={(event: ChangeEvent<HTMLInputElement>): void =>
              onSelect(event.target.value as FitChefSupportNeed)
            }
          />
          <RadioGroupOption
            checked={selectedNeed === 'weekly_structure'}
            description="Request one bounded pointer for the week."
            label="Help me structure my week"
            name="fitchef-support-need"
            value="weekly_structure"
            onChange={(event: ChangeEvent<HTMLInputElement>): void =>
              onSelect(event.target.value as FitChefSupportNeed)
            }
          />
        </RadioGroup>

        {authState === 'unknown' ? (
          <p className="text-sm font-medium text-[var(--color-text-muted)]" role="status">
            Checking session before this request can be sent.
          </p>
        ) : null}

        {authState === 'unauthenticated' ? (
          <Alert tone="info" title="Access required">
            <p>{UNAUTHENTICATED_COPY}</p>
          </Alert>
        ) : null}

        {state.status === 'success' || state.status === 'confirmed' ? (
          <Alert
            tone={state.status === 'confirmed' ? 'success' : 'info'}
            title={state.status === 'confirmed' ? 'Pointer acknowledged' : 'Next-step pointer'}
          >
            <p data-testid="fitchef-support-result-copy">
              {RESULT_COPY[state.result.action.target_surface]}
            </p>
            <p className="mt-2">
              <span className="font-semibold">Product area:</span>{' '}
              <span data-testid="fitchef-support-target-label">
                {TARGET_LABELS[state.result.action.target_surface]}
              </span>
            </p>
            {state.status === 'success' ? (
              <div className="mt-3">
                <Button onClick={onConfirm}>I understand this next step</Button>
              </div>
            ) : (
              <p className="mt-3 font-medium" data-testid="fitchef-support-confirmed-copy">
                {CONFIRMED_COPY}
              </p>
            )}
          </Alert>
        ) : null}

        {state.status === 'error' ? (
          <Alert tone="error" title="Next-step pointer unavailable">
            <p>{ERROR_COPY[state.errorCategory]}</p>
          </Alert>
        ) : null}

        {state.status === 'dismissed' ? (
          <Alert tone="info" title="Next-step pointer dismissed">
            <p>
              Nothing has been opened or run. No plan has been created or changed. Choose an option
              whenever you want to start again.
            </p>
          </Alert>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <Button
            data-fitchef-support-submit="true"
            disabled={!canSubmit}
            loading={isPending}
            loadingLabel="Loading next step…"
            onClick={onSubmit}
          >
            {submitLabel}
          </Button>
          {state.status !== 'dismissed' ? (
            <Button variant="ghost" onClick={onDismiss}>
              Not now
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function SupportChoiceCard({
  authState,
  requester = requestFitChefSupportHandoff,
}: SupportChoiceCardProps): ReactElement {
  const [state, setState] = useState<SupportChoiceViewState>({
    status: 'idle',
    selectedNeed: null,
    result: null,
    errorCategory: null,
  });
  const rootRef = useRef<HTMLElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestSequenceRef = useRef(0);
  const mountedRef = useRef(false);
  const viewedRef = useRef(false);
  const confirmationRecordedRef = useRef(false);
  const submittedAuthStateRef = useRef<'authenticated'>('authenticated');
  const submittedLifecycleRef = useRef<SubmittedSupportLifecycle | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    if (!viewedRef.current) {
      viewedRef.current = true;
      trackFitChefSupportChoiceEvent({
        name: 'fitchef_support_choice_viewed',
        payload: BASE_EVENT_PAYLOAD,
      });
    }

    return () => {
      mountedRef.current = false;
      requestSequenceRef.current += 1;
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      submittedLifecycleRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (state.status === 'error') {
      rootRef.current
        ?.querySelector<HTMLButtonElement>('[data-fitchef-support-submit="true"]')
        ?.focus();
    }
  }, [state.status]);

  function stopCurrentRequest(): void {
    requestSequenceRef.current += 1;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }

  function terminateSubmittedLifecycle(outcome: FitChefSupportExitOutcome): boolean {
    const lifecycle = submittedLifecycleRef.current;
    if (lifecycle === null || lifecycle.terminated) {
      return false;
    }

    lifecycle.terminated = true;
    trackFitChefSupportChoiceEvent({
      name: 'fitchef_support_handoff_exited',
      payload: {
        ...BASE_EVENT_PAYLOAD,
        outcome,
        supportNeed: lifecycle.supportNeed,
        ...(lifecycle.targetSurface === undefined
          ? {}
          : { targetSurface: lifecycle.targetSurface }),
      },
    });
    return true;
  }

  function selectSupportNeed(supportNeed: FitChefSupportNeed): void {
    if (supportNeed === state.selectedNeed) {
      return;
    }

    if (state.status === 'pending' || state.status === 'success' || state.status === 'confirmed') {
      terminateSubmittedLifecycle('changed_selection');
    }
    stopCurrentRequest();
    submittedLifecycleRef.current = null;
    confirmationRecordedRef.current = false;
    setState({
      status: 'ready',
      selectedNeed: supportNeed,
      result: null,
      errorCategory: null,
    });
  }

  async function submitSupportNeed(): Promise<void> {
    if (
      state.selectedNeed === null ||
      authState !== 'authenticated' ||
      (state.status !== 'ready' && state.status !== 'error')
    ) {
      return;
    }

    const submittedNeed = state.selectedNeed;
    const submittedAuthState = authState;
    submittedAuthStateRef.current = submittedAuthState;
    const controller = new AbortController();
    abortControllerRef.current?.abort();
    abortControllerRef.current = controller;
    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    confirmationRecordedRef.current = false;
    submittedLifecycleRef.current = {
      supportNeed: submittedNeed,
      terminated: false,
    };

    trackFitChefSupportChoiceEvent({
      name: 'fitchef_support_need_selected',
      payload: {
        ...BASE_EVENT_PAYLOAD,
        supportNeed: submittedNeed,
        authState: submittedAuthState,
      },
    });
    setState({
      status: 'pending',
      selectedNeed: submittedNeed,
      result: null,
      errorCategory: null,
    });

    try {
      const result = await requester(submittedNeed, {
        signal: controller.signal,
        onAuthError: () => undefined,
      });
      if (
        !mountedRef.current ||
        controller.signal.aborted ||
        requestSequence !== requestSequenceRef.current
      ) {
        return;
      }

      abortControllerRef.current = null;
      const lifecycle = submittedLifecycleRef.current;
      if (
        lifecycle !== null &&
        !lifecycle.terminated &&
        lifecycle.supportNeed === submittedNeed
      ) {
        lifecycle.targetSurface = result.action.target_surface;
      }
      setState({
        status: 'success',
        selectedNeed: submittedNeed,
        result,
        errorCategory: null,
      });
      trackFitChefSupportChoiceEvent({
        name: 'fitchef_support_handoff_received',
        payload: {
          ...BASE_EVENT_PAYLOAD,
          supportNeed: result.support_need,
          targetSurface: result.action.target_surface,
          authState: submittedAuthState,
        },
      });
    } catch (error) {
      if (
        !mountedRef.current ||
        controller.signal.aborted ||
        requestSequence !== requestSequenceRef.current ||
        isAbortError(error)
      ) {
        return;
      }

      abortControllerRef.current = null;
      const errorCategory = classifyError(error);
      const errorState: SupportChoiceViewState = {
        status: 'error',
        selectedNeed: submittedNeed,
        result: null,
        errorCategory,
      };
      setState(errorState);
      terminateSubmittedLifecycle(errorCategory);
    }
  }

  function confirmSupportNeed(): void {
    if (state.status !== 'success' || confirmationRecordedRef.current) {
      return;
    }

    confirmationRecordedRef.current = true;
    setState({ ...state, status: 'confirmed' });
    trackFitChefSupportChoiceEvent({
      name: 'fitchef_support_handoff_confirmed',
      payload: {
        ...BASE_EVENT_PAYLOAD,
        supportNeed: state.result.support_need,
        targetSurface: state.result.action.target_surface,
        authState: submittedAuthStateRef.current,
      },
    });
  }

  function dismissSupportChoice(): void {
    stopCurrentRequest();
    confirmationRecordedRef.current = false;
    terminateSubmittedLifecycle('dismissed');
    submittedLifecycleRef.current = null;
    setState({
      status: 'dismissed',
      selectedNeed: null,
      result: null,
      errorCategory: null,
    });
  }

  return (
    <section ref={rootRef} aria-label="FitChef support choice">
      <SupportChoiceCardView
        authState={authState}
        state={state}
        onConfirm={confirmSupportNeed}
        onDismiss={dismissSupportChoice}
        onSelect={selectSupportNeed}
        onSubmit={(): void => {
          void submitSupportNeed();
        }}
      />
    </section>
  );
}

export default SupportChoiceCard;
