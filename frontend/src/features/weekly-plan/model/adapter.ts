/**
 * Weekly plan adapter.
 *
 * Normalizes canonical API payloads into a stable UI view model.
 */

import type { RawDayMenu, RawMeal, RawWeekPlanResponse, WeekPlanVM, DayMenu, Meal } from './types';

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const;
const BLOCKED_OBJECT_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function safeNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function safeString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function normalizeNumericMap(raw: unknown): Record<string, number> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return {};
  }

  const normalized: Record<string, number> = Object.create(null);
  for (const [key, value] of Object.entries(raw)) {
    if (BLOCKED_OBJECT_KEYS.has(key)) {
      continue;
    }

    if (typeof value === 'number' && Number.isFinite(value)) {
      normalized[key] = value;
    }
  }

  return normalized;
}

function normalizeTips(raw: unknown): string[] {
  return Array.isArray(raw) ? raw.filter((tip): tip is string => typeof tip === 'string') : [];
}

function normalizeMeal(raw: RawMeal): Meal {
  return {
    title: safeString(raw.title, 'Untitled meal'),
    title_translated: safeString(raw.title_translated, safeString(raw.title, 'Untitled meal')),
    kcal: safeNumber(raw.kcal),
    price_est: raw.price_est == null ? null : safeNumber(raw.price_est, 0),
    grams: normalizeNumericMap(raw.grams),
    macros: normalizeNumericMap(raw.macros),
    micros: normalizeNumericMap(raw.micros),
  };
}

function normalizeDayMenu(raw: RawDayMenu, index: number): DayMenu {
  const day = index + 1;
  const payload =
    raw && typeof raw === 'object' && !Array.isArray(raw)
      ? raw
      : ({
          meals: [],
          kcal: 0,
          macros: {},
          micros: {},
          coverage: {},
          tips: [],
          total_cost: 0,
        } as RawDayMenu);

  return {
    day,
    dayName: DAY_NAMES[index] ?? `Day ${day}`,
    meals: Array.isArray(payload.meals) ? payload.meals.map(normalizeMeal) : [],
    kcal: safeNumber(payload.kcal),
    macros: normalizeNumericMap(payload.macros),
    micros: normalizeNumericMap(payload.micros),
    coverage: normalizeNumericMap(payload.coverage),
    tips: normalizeTips(payload.tips),
    total_cost: safeNumber(payload.total_cost),
  };
}

function normalizeWeeklyCoverage(
  raw: RawWeekPlanResponse['weekly_coverage']
): WeekPlanVM['weekly_coverage'] {
  const normalized = normalizeNumericMap(raw);

  return {
    protein: clamp(safeNumber(normalized.protein), 0, 300),
    iron: clamp(safeNumber(normalized.iron), 0, 300),
    vitamin_c: clamp(safeNumber(normalized.vitamin_c), 0, 300),
    calcium: clamp(safeNumber(normalized.calcium), 0, 300),
    ...Object.fromEntries(
      Object.entries(normalized).map(([key, value]) => [key, clamp(value, 0, 300)])
    ),
  };
}

export function normalizeWeekPlan(raw: RawWeekPlanResponse): WeekPlanVM {
  const dailyMenus = Array.isArray(raw.daily_menus) ? raw.daily_menus : [];
  const days = dailyMenus.map(normalizeDayMenu);
  const shoppingList = normalizeNumericMap(raw.shopping_list);

  return {
    days,
    weekly_coverage: normalizeWeeklyCoverage(raw.weekly_coverage),
    shopping_list: shoppingList,
    metrics: {
      total_cost: safeNumber(raw.total_cost),
      adherence_score: clamp(safeNumber(raw.adherence_score), 0, 1),
    },
    meta: {
      total_days: days.length,
      has_incomplete_data: false,
    },
  };
}
