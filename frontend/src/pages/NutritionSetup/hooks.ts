// RU: Хуки для работы с API расчетов в Nutrition Setup
// EN: Hooks for API calculations in Nutrition Setup

import { useState, useEffect, useMemo, useRef } from 'react';
import { getBmr } from '../../api/client';
import type { SetupFormValues, EnrichedBmrResponse, PlateResponse, TargetsResponse } from './schema';
import { mockPlateData } from './mocks';

export function useSetupCalc(values: SetupFormValues | null) {
  const [bmrData, setBmrData] = useState<EnrichedBmrResponse | null>(null);
  const [plateData, setPlateData] = useState<PlateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const enabled = !!values;

  useEffect(() => {
    if (!enabled) {
      setBmrData(null);
      setPlateData(null);
      setError(null);
      return;
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this effect run
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

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

        const bmrResult = await getBmr(bmrRequest, { signal: abortController.signal });

        // Calculate TDEE based on BMR and activity level
        const activityMultipliers = {
          sedentary: 1.2,
          light: 1.375,
          moderate: 1.55,
          active: 1.725,
          athlete: 1.9,
        };

        const multiplier = activityMultipliers[values.activity] || 1.55; // default to moderate
        const tdee = Math.round(bmrResult.bmr * multiplier);

        setBmrData({
          ...bmrResult,
          tdee,
        });

        // TODO: Replace with real getPlate() call once API supports goal/diet_flags parameters
        // Currently using mock data because getPlate() API doesn't accept goal and diet_flags yet
        setPlateData(mockPlateData);

      } catch (err) {
        // Don't set error state if request was aborted
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        console.error('Nutrition setup calculation error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Cleanup function
    return () => {
      abortController.abort();
    };
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

  // Localized mock data - will be replaced with real API call when /premium/targets supports i18n
  const localizedTargets = useMemo(() => {
    const targetsData = {
      ru: [
        { id: 'fe', name: 'Железо', unit: 'мг', target: 18 },
        { id: 'ca', name: 'Кальций', unit: 'мг', target: 1000 },
        { id: 'k', name: 'Калий', unit: 'мг', target: 4700 },
        { id: 'mg', name: 'Магний', unit: 'мг', target: 400 },
        { id: 'zn', name: 'Цинк', unit: 'мг', target: 11 },
        { id: 'i', name: 'Йод', unit: 'мкг', target: 150 },
        { id: 'd', name: 'Витамин D', unit: 'МЕ', target: 600 },
        { id: 'b12', name: 'Витамин B12', unit: 'мкг', target: 2.4 },
      ],
      en: [
        { id: 'fe', name: 'Iron', unit: 'mg', target: 18 },
        { id: 'ca', name: 'Calcium', unit: 'mg', target: 1000 },
        { id: 'k', name: 'Potassium', unit: 'mg', target: 4700 },
        { id: 'mg', name: 'Magnesium', unit: 'mg', target: 400 },
        { id: 'zn', name: 'Zinc', unit: 'mg', target: 11 },
        { id: 'i', name: 'Iodine', unit: 'mcg', target: 150 },
        { id: 'd', name: 'Vitamin D', unit: 'IU', target: 600 },
        { id: 'b12', name: 'Vitamin B12', unit: 'mcg', target: 2.4 },
      ],
      es: [
        { id: 'fe', name: 'Hierro', unit: 'mg', target: 18 },
        { id: 'ca', name: 'Calcio', unit: 'mg', target: 1000 },
        { id: 'k', name: 'Potasio', unit: 'mg', target: 4700 },
        { id: 'mg', name: 'Magnesio', unit: 'mg', target: 400 },
        { id: 'zn', name: 'Zinc', unit: 'mg', target: 11 },
        { id: 'i', name: 'Yodo', unit: 'mcg', target: 150 },
        { id: 'd', name: 'Vitamina D', unit: 'IU', target: 600 },
        { id: 'b12', name: 'Vitamina B12', unit: 'mcg', target: 2.4 },
      ],
    };

    return targetsData[lang] || targetsData.ru;
  }, [lang]);

  useEffect(() => {
    const fetchTargets = async () => {
      setLoading(true);
      setError(null);

      try {
        // TODO: Replace with real /premium/targets API call when it supports i18n
        // Currently using localized mock data
        const mockTargets: TargetsResponse = {
          micros: localizedTargets,
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
