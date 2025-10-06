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
        // For now, mock the plate result since API may not support these params yet
        const plateResult = {
          plate: {
            carbs_pct: 50,
            protein_pct: 25,
            fat_pct: 25,
            kcal: 2000,
          },
          macros: {
            carbs_g: 250,
            protein_g: 125,
            fat_g: 55,
            fiber_g: 25,
          },
          water_l: 2.5,
        };
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
        // For now, return mock data since /premium/targets endpoint may not exist yet
        const mockTargets: TargetsResponse = {
          micros: [
            { id: 'fe', name: 'Железо', unit: 'мг', target: 18 },
            { id: 'ca', name: 'Кальций', unit: 'мг', target: 1000 },
            { id: 'k', name: 'Калий', unit: 'мг', target: 4700 },
            { id: 'mg', name: 'Магний', unit: 'мг', target: 400 },
            { id: 'zn', name: 'Цинк', unit: 'мг', target: 11 },
            { id: 'i', name: 'Йод', unit: 'мкг', target: 150 },
            { id: 'd', name: 'Витамин D', unit: 'МЕ', target: 600 },
            { id: 'b12', name: 'Витамин B12', unit: 'мкг', target: 2.4 },
          ]
        };

        setData(mockTargets);
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
