/**
 * Weekly plan adapter.
 *
 * Normalizes canonical API payloads into a stable UI view model.
 */

import type { RawDayMenu, RawMeal, RawWeekPlanResponse, WeekPlanVM, DayMenu, Meal } from './types';

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const;
const BLOCKED_OBJECT_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

interface NormalizationState {
  incomplete: boolean;
}

function markIncomplete(state: NormalizationState): void {
  state.incomplete = true;
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function safeRequiredNumber(value: unknown, fallback: number, state: NormalizationState): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  markIncomplete(state);
  return fallback;
}

function safeNullableNumber(value: unknown, state: NormalizationState): number | null {
  if (value == null) {
    return null;
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  markIncomplete(state);
  return null;
}

function safeString(value: unknown, fallback: string, state: NormalizationState): string {
  if (typeof value === 'string') {
    return value;
  }

  markIncomplete(state);
  return fallback;
}

function normalizeNumericMap(raw: unknown, state: NormalizationState): Record<string, number> {
  if (!isObjectRecord(raw)) {
    markIncomplete(state);
    return {};
  }

  const normalized: Record<string, number> = Object.create(null);
  for (const [key, value] of Object.entries(raw)) {
    if (BLOCKED_OBJECT_KEYS.has(key)) {
      markIncomplete(state);
      continue;
    }

    if (typeof value === 'number' && Number.isFinite(value)) {
      normalized[key] = value;
    } else {
      markIncomplete(state);
    }
  }

  return normalized;
}

function normalizeTips(raw: unknown, state: NormalizationState): string[] {
  if (!Array.isArray(raw)) {
    markIncomplete(state);
    return [];
  }

  const normalized: string[] = [];
  raw.forEach((tip) => {
    if (typeof tip === 'string') {
      normalized.push(tip);
    } else {
      markIncomplete(state);
    }
  });
  return normalized;
}

function normalizeMeal(raw: unknown, state: NormalizationState): Meal {
  const payload = isObjectRecord(raw) ? raw : {};
  if (!isObjectRecord(raw)) {
    markIncomplete(state);
  }

  const title = safeString(payload.title, 'Untitled meal', state);
  const titleTranslated = safeString(payload.title_translated, title, state);

  return {
    title,
    title_translated: titleTranslated,
    kcal: safeRequiredNumber(payload.kcal, 0, state),
    price_est: safeNullableNumber(payload.price_est, state),
    grams: normalizeNumericMap(payload.grams, state),
    macros: normalizeNumericMap(payload.macros, state),
    micros: normalizeNumericMap(payload.micros, state),
  };
}

function normalizeDayMenu(raw: unknown, index: number, state: NormalizationState): DayMenu {
  const day = index + 1;
  const payload: Partial<RawDayMenu> = isObjectRecord(raw) ? raw : {};
  if (!isObjectRecord(raw)) {
    markIncomplete(state);
  }

  const meals = Array.isArray(payload.meals)
    ? payload.meals
        .filter((meal): meal is RawMeal => {
          const isValid = isObjectRecord(meal);
          if (!isValid) {
            markIncomplete(state);
          }
          return isValid;
        })
        .map((meal) => normalizeMeal(meal, state))
    : (markIncomplete(state), []);

  return {
    day,
    dayName: DAY_NAMES[index] ?? `Day ${day}`,
    meals,
    kcal: safeRequiredNumber(payload.kcal, 0, state),
    macros: normalizeNumericMap(payload.macros, state),
    micros: normalizeNumericMap(payload.micros, state),
    coverage: normalizeNumericMap(payload.coverage, state),
    tips: normalizeTips(payload.tips, state),
    total_cost: safeRequiredNumber(payload.total_cost, 0, state),
  };
}

function normalizeWeeklyCoverage(
  raw: RawWeekPlanResponse['weekly_coverage'],
  state: NormalizationState
): WeekPlanVM['weekly_coverage'] {
  return normalizeNumericMap(raw, state);
}

export function normalizeWeekPlan(raw: RawWeekPlanResponse): WeekPlanVM {
  const state: NormalizationState = { incomplete: false };
  const days = Array.isArray(raw.daily_menus)
    ? raw.daily_menus.flatMap((menu, index) => {
        if (!isObjectRecord(menu)) {
          markIncomplete(state);
          return [];
        }

        return [normalizeDayMenu(menu, index, state)];
      })
    : (markIncomplete(state), []);
  const shoppingList = normalizeNumericMap(raw.shopping_list, state);

  return {
    days,
    weekly_coverage: normalizeWeeklyCoverage(raw.weekly_coverage, state),
    shopping_list: shoppingList,
    metrics: {
      total_cost: safeRequiredNumber(raw.total_cost, 0, state),
      adherence_score: safeRequiredNumber(raw.adherence_score, 0, state),
    },
    meta: {
      total_days: days.length,
      has_incomplete_data: state.incomplete,
    },
  };
}
