import { useReducer } from 'react';
import type { JSX } from 'react';
import fitChefPreview from '../../assets/brand/fitchef-onboarding-welcome-v1.png';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { RadioGroup, RadioGroupOption } from '../ui/RadioGroup';
import { MarketingSection, SectionHeader } from './MarketingPrimitives';

export type FitChefDemoChoice = 'today' | 'week';

export type FitChefDemoState =
  | { status: 'idle' }
  | { status: 'selected'; choice: FitChefDemoChoice }
  | { status: 'revealed'; choice: FitChefDemoChoice };

export type FitChefDemoEvent =
  | { type: 'select'; choice: FitChefDemoChoice }
  | { type: 'confirm' }
  | { type: 'reset' };

export const FITCHEF_DEMO_INITIAL_STATE: FitChefDemoState = { status: 'idle' };

function isChoice(value: unknown): value is FitChefDemoChoice {
  return value === 'today' || value === 'week';
}

export function fitChefValueDemoReducer(
  state: FitChefDemoState,
  event: unknown,
): FitChefDemoState {
  if (typeof event !== 'object' || event === null || !('type' in event)) {
    return state;
  }

  const candidate = event as { type?: unknown; choice?: unknown };

  if (candidate.type === 'reset') {
    return state.status === 'idle' ? state : FITCHEF_DEMO_INITIAL_STATE;
  }

  if (candidate.type === 'confirm') {
    if (state.status !== 'selected') {
      return state;
    }

    return { status: 'revealed', choice: state.choice };
  }

  if (candidate.type !== 'select' || !isChoice(candidate.choice)) {
    return state;
  }

  if (state.status !== 'idle' && state.choice === candidate.choice) {
    return state;
  }

  return { status: 'selected', choice: candidate.choice };
}

const optionCopy: Record<
  FitChefDemoChoice,
  { label: string; detail: string; result: string }
> = {
  today: {
    label: 'Today',
    detail: 'Start with the plan for today.',
    result: 'For today, FitChef would point to Daily Plate.',
  },
  week: {
    label: 'This week',
    detail: 'Look at the next seven days.',
    result: 'For this week, FitChef would point to Weekly Planning.',
  },
};

export function FitChefValueDemo(): JSX.Element {
  const [state, dispatch] = useReducer(fitChefValueDemoReducer, FITCHEF_DEMO_INITIAL_STATE);
  const selectedChoice = state.status === 'idle' ? null : state.choice;
  const result = state.status === 'revealed' ? optionCopy[state.choice].result : null;

  const selectChoice = (choice: FitChefDemoChoice): void => {
    dispatch({ type: 'select', choice });
  };

  return (
    <MarketingSection className="ppm-fitchef-demo-section" id="fitchef-demo">
      <SectionHeader
        description="FitChef shows both options. The choice is yours."
        title="See how FitChef helps you choose where to start"
      />

      <Card className="ppm-fitchef-demo-card" data-testid="fitchef-value-demo">
        <div className="ppm-fitchef-demo-layout">
          <div className="ppm-fitchef-demo-intro">
            <img
              alt="FitChef, the PulsePlate wellness guide"
              className="ppm-fitchef-demo-image"
              src={fitChefPreview}
            />
            <div>
              <p className="ppm-fitchef-demo-consequence">
                For now, you’re only choosing where to start. Nothing will open, be saved, or
                change.
              </p>
              <p className="ppm-fitchef-demo-wellness">
                For everyday planning — not medical advice.
              </p>
            </div>
          </div>

          <div className="ppm-fitchef-choice-group">
            <RadioGroup legend="Where would you like to start?">
              {(Object.keys(optionCopy) as FitChefDemoChoice[]).map((choice) => {
                const copy = optionCopy[choice];
                const isSelected = selectedChoice === choice;

                return (
                  <RadioGroupOption
                    key={choice}
                    aria-checked={isSelected}
                    checked={isSelected}
                    className={[
                      'ppm-fitchef-option',
                      isSelected ? 'ppm-fitchef-option--selected' : '',
                    ]
                      .join(' ')
                      .trim()}
                    description={
                      <span className="ppm-fitchef-option-detail">{copy.detail}</span>
                    }
                    label={<span className="ppm-fitchef-option-label">{copy.label}</span>}
                    name="fitchef-start"
                    value={choice}
                    onChange={() => selectChoice(choice)}
                  />
                );
              })}
            </RadioGroup>

            <div className="ppm-fitchef-demo-actions">
              <Button
                className="ppm-fitchef-confirm"
                disabled={selectedChoice === null}
                onClick={() => dispatch({ type: 'confirm' })}
              >
                Confirm choice
              </Button>
              <Button
                className="ppm-fitchef-secondary"
                variant="secondary"
                onClick={() => dispatch({ type: 'reset' })}
              >
                Not now
              </Button>
            </div>

            <div
              aria-atomic="true"
              aria-live="polite"
              className="ppm-fitchef-demo-result"
              role="status"
            >
              {result ? (
                <div>
                  <h3>A place to begin</h3>
                  <p>{result}</p>
                </div>
              ) : null}
            </div>

            <p className="ppm-fitchef-demo-disclosure">
              This is a prepared website example. It does not run AI, use personal data, open
              anything, or change a plan.
            </p>
          </div>
        </div>
      </Card>
    </MarketingSection>
  );
}

export default FitChefValueDemo;
