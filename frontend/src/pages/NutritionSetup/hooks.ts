// RU: Хуки для работы с API расчетов в Nutrition Setup
// EN: Hooks for API calculations in Nutrition Setup

import { useState, useEffect, useMemo } from 'react';
import { getBmr, getPlate, getWeekPlan } from '../../api/client';
import type { SetupFormValues, BmrResponse, PlateResponse, TargetsResponse } from './schema';

export function useSetupCalc(values: SetupFormValues | null) {
  const [bmrData, setBmrData] = useState<BmrResponse | null>(null);
  const [plateData, setPlateData] = useState<PlateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enabled = !!values;

  useEffect(() => {
    if (!enabled) {
      setBmrData(null);
      setPlateData(null);
      setError(null);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch BMR
        const bmrRequest = {
          sex: values.sex,
          age: values.age,
          height: values.height_cm,
          weight: values.weight_kg,
        };

        const bmrResult = await getBmr(bmrRequest);
        setBmrData(bmrResult);

        // Fetch Plate (using goal and diet flags)
        const plateRequest = {
          goal: values.goal,
          diet_flags: values.diet_flags,
        };
        // Fetch Plate data from API
        const plateResult = await getPlate(plateRequest);
        setPlateData(plateResult);

      } catch (err) {
        console.error('Nutrition setup calculation error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [enabled, values]);

  return {
    bmrData,
    plateData,
    loading,
    error,
    enabled,
  };
}

export function useTargets(lang: "ru" | "en" | "es" = "ru") {
  const [data, setData] = useState<TargetsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTargets = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch targets from mock API file
        const response = await fetch('/mocks/premium/targets.json');
        if (!response.ok) {
          throw new Error(`Failed to fetch targets: ${response.statusText}`);
        }
        const targets: TargetsResponse = await response.json();
        setData(targets);
      } catch (err) {
        console.error('Targets fetch error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchTargets();
  }, [lang]);

  return {
    data,
    loading,
    error,
  };
}
