import { useReducer } from 'react';
import type { JSX } from 'react';
import enduranceImage from '../../assets/brand/fitchef-public-demo/v1/activity-palette/endurance.webp';
import movementImage from '../../assets/brand/fitchef-public-demo/v1/activity-palette/movement-everyday-fitness.webp';
import strengthImage from '../../assets/brand/fitchef-public-demo/v1/activity-palette/strength-power.webp';
import teamImage from '../../assets/brand/fitchef-public-demo/v1/activity-palette/team-combat.webp';
import dailyPlateImage from '../../assets/brand/fitchef-public-demo/v1/daily-plate-a-salmon-1024.webp';
import ingredientsImage from '../../assets/brand/fitchef-public-demo/v1/food-context/food-context-ingredients-at-home.webp';
import mealPhotoImage from '../../assets/brand/fitchef-public-demo/v1/food-context/food-context-meal-photo.webp';
import restaurantImage from '../../assets/brand/fitchef-public-demo/v1/food-context/food-context-restaurant-chef.webp';
import shoppingImage from '../../assets/brand/fitchef-public-demo/v1/food-context/food-context-shopping-stores.webp';
import vipFitChefImage from '../../assets/brand/fitchef-public-demo/v1/vip/fitchef-vip-editorial-owner-approved-logo-v2.webp';
import weeklyPlanningImage from '../../assets/brand/fitchef-public-demo/v1/weekly-planning-a-meal-grid-1024.webp';
import weeklyNotebookImage from '../../assets/brand/fitchef-public-demo/v1/weekly-planning-b-notebook-1024.webp';
import fitChefNeutral from '../../assets/brand/fitchef-portrait-neutral-v1.png';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { RadioGroup, RadioGroupOption } from '../ui/RadioGroup';
import {
  MarketingCard,
  MarketingSection,
  SectionHeader,
  StatusPill,
} from './MarketingPrimitives';

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

const optionCopy: Record<FitChefDemoChoice, { label: string; detail: string }> = {
  today: {
    label: 'Today',
    detail: 'Start with the plan for today.',
  },
  week: {
    label: 'This week',
    detail: 'Look at the next seven days.',
  },
};

const activityPalette = [
  {
    asset: 'activity-palette/endurance.webp',
    className: 'ppm-fitchef-activity--endurance',
    image: enduranceImage,
    label: 'Endurance',
  },
  {
    asset: 'activity-palette/strength-power.webp',
    className: 'ppm-fitchef-activity--strength',
    image: strengthImage,
    label: 'Strength & Power',
  },
  {
    asset: 'activity-palette/team-combat.webp',
    className: 'ppm-fitchef-activity--team',
    image: teamImage,
    label: 'Team & Combat',
  },
  {
    asset: 'activity-palette/movement-everyday-fitness.webp',
    className: 'ppm-fitchef-activity--movement',
    image: movementImage,
    label: 'Movement & Everyday Fitness',
  },
] as const;

const foodContexts = [
  {
    asset: 'food-context/food-context-ingredients-at-home.webp',
    className: 'ppm-fitchef-context-card--ingredients',
    image: ingredientsImage,
    label: 'Ingredients at home',
  },
  {
    asset: 'food-context/food-context-restaurant-chef.webp',
    className: 'ppm-fitchef-context-card--restaurant',
    image: restaurantImage,
    label: 'Restaurant or chef',
  },
  {
    asset: 'food-context/food-context-shopping-stores.webp',
    className: 'ppm-fitchef-context-card--shopping',
    image: shoppingImage,
    label: 'Shopping and stores',
  },
  {
    asset: 'food-context/food-context-meal-photo.webp',
    className: 'ppm-fitchef-context-card--photo',
    image: mealPhotoImage,
    label: 'A food photo',
  },
] as const;

function ActivityPalette(): JSX.Element {
  return (
    <section className="ppm-fitchef-context-block" aria-labelledby="fitchef-movement-title">
      <h3 className="ppm-fitchef-context-title" id="fitchef-movement-title">
        Ways to move
      </h3>
      <MarketingCard className="ppm-fitchef-activity-rail">
        {activityPalette.map(({ asset, className, image, label }) => (
          <article className={['ppm-fitchef-photo-card', className].join(' ')} key={asset}>
            <img
              alt=""
              aria-hidden="true"
              data-fitchef-asset={asset}
              decoding="async"
              loading="lazy"
              src={image}
            />
            <span>{label}</span>
          </article>
        ))}
      </MarketingCard>
    </section>
  );
}

function GoalSpectrum(): JSX.Element {
  return (
    <MarketingCard className="ppm-fitchef-goal-card">
      <h3 className="ppm-fitchef-context-title">Goal</h3>
      <div className="ppm-fitchef-goal-spectrum">
        <StatusPill className="ppm-fitchef-goal-state ppm-fitchef-goal-state--reduce">
          Reduce
        </StatusPill>
        <StatusPill className="ppm-fitchef-goal-state ppm-fitchef-goal-state--maintain">
          Maintain
        </StatusPill>
        <StatusPill className="ppm-fitchef-goal-state ppm-fitchef-goal-state--gain">
          Gain
        </StatusPill>
      </div>
    </MarketingCard>
  );
}

function RevealedPlanningView({ choice }: { choice: FitChefDemoChoice }): JSX.Element {
  const isToday = choice === 'today';
  const heading = isToday ? 'Daily Plate' : 'Weekly Planning';
  const asset = isToday
    ? 'daily-plate-a-salmon-1024.webp'
    : 'weekly-planning-a-meal-grid-1024.webp';
  const image = isToday ? dailyPlateImage : weeklyPlanningImage;

  return (
    <Card
      aria-atomic="true"
      aria-live="polite"
      className="ppm-fitchef-reveal-card"
      role="status"
    >
      <h3>{heading}</h3>
      <figure className="ppm-fitchef-reveal-photo">
        <img
          alt=""
          aria-hidden="true"
          data-fitchef-asset={asset}
          decoding="async"
          height={1024}
          loading="lazy"
          src={image}
          width={1024}
        />
      </figure>
    </Card>
  );
}

function DailyStory(): JSX.Element {
  const [state, dispatch] = useReducer(fitChefValueDemoReducer, FITCHEF_DEMO_INITIAL_STATE);
  const selectedChoice = state.status === 'idle' ? null : state.choice;

  return (
    <section className="ppm-fitchef-story ppm-fitchef-daily-story" data-fitchef-story="daily">
      <SectionHeader
        className="ppm-fitchef-story-header"
        description="FitChef shows both options. The choice is yours."
        title="See how FitChef helps you choose where to start"
      />

      <div className="ppm-fitchef-context-grid">
        <ActivityPalette />
        <GoalSpectrum />
      </div>

      <span className="ppm-fitchef-context-bridge" aria-hidden="true" />

      <div className="ppm-fitchef-daily-flow">
        <Card className="ppm-fitchef-choice-card">
          <span className="ppm-fitchef-neutral-slot" aria-hidden="true">
            <img
              alt=""
              aria-hidden="true"
              decoding="async"
              height={76}
              loading="lazy"
              src={fitChefNeutral}
              width={76}
            />
          </span>

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
                    onChange={() => dispatch({ type: 'select', choice })}
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
          </div>
        </Card>

        {state.status === 'revealed' ? (
          <RevealedPlanningView choice={state.choice} />
        ) : null}
      </div>
    </section>
  );
}

function WeeklyStory(): JSX.Element {
  return (
    <section className="ppm-fitchef-story ppm-fitchef-weekly-story" data-fitchef-story="weekly">
      <SectionHeader className="ppm-fitchef-story-header" title="A week that changes with you" />

      <div className="ppm-fitchef-weekly-flow">
        <Card className="ppm-fitchef-weekly-card">
          <h3>Starting week</h3>
          <figure className="ppm-fitchef-weekly-photo">
            <img
              alt=""
              aria-hidden="true"
              data-fitchef-asset="weekly-planning-b-notebook-1024.webp"
              decoding="async"
              height={1024}
              loading="lazy"
              src={weeklyNotebookImage}
              width={1024}
            />
          </figure>
        </Card>

        <span className="ppm-fitchef-weekly-arrow" aria-hidden="true" />

        <MarketingCard className="ppm-fitchef-weekly-changes">
          <h3>What changed</h3>
          <div className="ppm-fitchef-change-list">
            <article className="ppm-fitchef-change ppm-fitchef-change--goal">
              <span className="ppm-fitchef-change-spectrum" aria-hidden="true" />
              <span>Your goal changes</span>
            </article>
            <article className="ppm-fitchef-change">
              <span className="ppm-fitchef-change-thumb">
                <img
                  alt=""
                  aria-hidden="true"
                  data-fitchef-asset="food-context/food-context-restaurant-chef.webp"
                  decoding="async"
                  loading="lazy"
                  src={restaurantImage}
                />
              </span>
              <span>A meal out</span>
            </article>
            <article className="ppm-fitchef-change">
              <span className="ppm-fitchef-change-thumb">
                <img
                  alt=""
                  aria-hidden="true"
                  data-fitchef-asset="food-context/food-context-ingredients-at-home.webp"
                  decoding="async"
                  loading="lazy"
                  src={ingredientsImage}
                />
              </span>
              <span>Use what’s at home</span>
            </article>
          </div>
        </MarketingCard>

        <span className="ppm-fitchef-weekly-arrow" aria-hidden="true" />

        <Card className="ppm-fitchef-weekly-card ppm-fitchef-weekly-card--updated">
          <h3>Updated week</h3>
          <figure className="ppm-fitchef-weekly-photo">
            <img
              alt=""
              aria-hidden="true"
              data-fitchef-asset="weekly-planning-a-meal-grid-1024.webp"
              decoding="async"
              height={1024}
              loading="lazy"
              src={weeklyPlanningImage}
              width={1024}
            />
          </figure>
        </Card>
      </div>
    </section>
  );
}

function FoodContextStory(): JSX.Element {
  return (
    <section className="ppm-fitchef-story ppm-fitchef-food-story" data-fitchef-story="food-context">
      <SectionHeader
        className="ppm-fitchef-story-header"
        title="A food plan built around real life"
      />

      <MarketingCard className="ppm-fitchef-food-context-rail">
        {foodContexts.map(({ asset, className, image, label }) => (
          <article className={['ppm-fitchef-photo-card', className].join(' ')} key={asset}>
            <img
              alt=""
              aria-hidden="true"
              data-fitchef-asset={asset}
              decoding="async"
              loading="lazy"
              src={image}
            />
            <span>{label}</span>
          </article>
        ))}
      </MarketingCard>

      <span className="ppm-fitchef-food-arrow" aria-hidden="true" />

      <Card className="ppm-fitchef-food-output">
        <h3>One flexible plan</h3>
        <div className="ppm-fitchef-food-output-panes">
          <figure>
            <img
              alt=""
              aria-hidden="true"
              data-fitchef-asset="daily-plate-a-salmon-1024.webp"
              decoding="async"
              height={1024}
              loading="lazy"
              src={dailyPlateImage}
              width={1024}
            />
          </figure>
          <figure>
            <img
              alt=""
              aria-hidden="true"
              data-fitchef-asset="weekly-planning-b-notebook-1024.webp"
              decoding="async"
              height={1024}
              loading="lazy"
              src={weeklyNotebookImage}
              width={1024}
            />
          </figure>
        </div>
      </Card>
    </section>
  );
}

function VipStory(): JSX.Element {
  return (
    <section className="ppm-fitchef-story ppm-fitchef-vip-story" data-fitchef-story="vip">
      <MarketingCard className="ppm-fitchef-vip-editorial">
        <div className="ppm-fitchef-vip-copy">
          <p className="ppm-fitchef-vip-eyebrow">PulsePlate VIP</p>
          <h2>Your personal AI nutrition guide</h2>
          <p>
            FitChef brings your measurements, goals and routines into everyday action: reshaping
            menus when plans change and finding a practical next step when progress slows.
          </p>
          <p className="ppm-fitchef-vip-support">
            For everyday wellbeing, training, strength and muscle-building goals.
          </p>
          <p className="ppm-fitchef-vip-closing">Support to keep you moving forward.</p>
        </div>

        <figure className="ppm-fitchef-vip-photo" aria-hidden="true">
          <img
            alt=""
            aria-hidden="true"
            data-fitchef-asset="vip/fitchef-vip-editorial-owner-approved-logo-v2.webp"
            decoding="async"
            height={1402}
            loading="lazy"
            src={vipFitChefImage}
            width={1122}
          />
        </figure>
      </MarketingCard>
    </section>
  );
}

export function FitChefValueDemo(): JSX.Element {
  return (
    <MarketingSection className="ppm-fitchef-demo-section" id="fitchef-demo">
      <Card className="ppm-fitchef-demo-card" data-testid="fitchef-value-demo">
        <DailyStory />
        <WeeklyStory />
        <FoodContextStory />
        <VipStory />
      </Card>
    </MarketingSection>
  );
}

export default FitChefValueDemo;
