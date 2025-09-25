import { useEffect, useState } from "react";
import type { components, paths } from "../../api/schema";
import { fetchJson } from "../../api/client";

type WeekPlanResponse =
  paths["/api/v1/premium/plan/week"]["post"]["responses"]["200"]["content"]["application/json"];
type WeekPlanRequest = components["schemas"]["WeekPlanRequest"];
type UnknownRecord = Record<string, unknown>;

const DEFAULT_REQUEST: WeekPlanRequest = {
  sex: "female",
  age: 30,
  height_cm: 168,
  weight_kg: 62,
  activity: "moderate",
  goal: "maintain",
  diet_flags: [],
  lang: "en",
};

export default function WeeklyPlanViewer() {
  const [data, setData] = useState<WeekPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const week = await fetchJson<WeekPlanResponse>("/api/v1/premium/plan/week", {
          method: "POST",
          body: JSON.stringify(DEFAULT_REQUEST),
        });
        setData(week);
      } catch (e: any) {
        setErr(e?.message || "Fetch error");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return <div className="max-w-3xl mx-auto p-6">Загружаем неделю…</div>;
  }

  if (err) {
    return (
      <div className="max-w-3xl mx-auto p-6 text-red-600">
        Ошибка загрузки плана: {err}
      </div>
    );
  }

  const dailyMenus = Array.isArray(data?.daily_menus)
    ? (data!.daily_menus as UnknownRecord[])
    : [];

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h2 className="text-xl font-semibold">Мой недельный план</h2>
      {dailyMenus.length === 0 && <div className="opacity-70">Пока пусто.</div>}
      <ul className="space-y-4">
        {dailyMenus.map((menu, idx) => {
          const day = menu as UnknownRecord;
          const dayTitle =
            typeof day.date === "string"
              ? day.date
              : typeof day.day_label === "string"
              ? day.day_label
              : `День ${idx + 1}`;
          const dayEnergy =
            typeof day.energy_kcal === "number"
              ? day.energy_kcal
              : typeof day.kcal === "number"
              ? day.kcal
              : undefined;

          const meals = Array.isArray(day.meals)
            ? (day.meals as UnknownRecord[])
            : [];

          return (
            <li key={dayTitle} className="border rounded-2xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="font-medium">{dayTitle}</div>
                {typeof dayEnergy === "number" && (
                  <div className="text-sm opacity-70">{Math.round(dayEnergy)} ккал/день</div>
                )}
              </div>
              <ul className="space-y-2">
                {meals.map((meal, mi) => {
                  const mealObj = meal as UnknownRecord;
                  const mealName =
                    typeof mealObj.name === "string"
                      ? mealObj.name
                      : typeof mealObj.meal === "string"
                      ? mealObj.meal
                      : `Приём ${mi + 1}`;
                  const mealEnergy =
                    typeof mealObj.energy_kcal === "number"
                      ? mealObj.energy_kcal
                      : typeof mealObj.kcal === "number"
                      ? mealObj.kcal
                      : undefined;

                  const rawItems = Array.isArray(mealObj.items)
                    ? (mealObj.items as UnknownRecord[])
                    : [];

                  const fallbackItem =
                    typeof mealObj.food_item === "string"
                      ? [
                          {
                            name: mealObj.food_item,
                            energy_kcal:
                              typeof mealObj.kcal === "number"
                                ? mealObj.kcal
                                : typeof mealObj.energy_kcal === "number"
                                ? mealObj.energy_kcal
                                : undefined,
                          },
                        ]
                      : [];

                  const items = rawItems.length > 0 ? rawItems : fallbackItem;

                  return (
                    <li key={`${mealName}-${mi}`} className="rounded-xl border p-3">
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{mealName}</div>
                        {typeof mealEnergy === "number" && (
                          <div className="text-sm opacity-70">{Math.round(mealEnergy)} ккал</div>
                        )}
                      </div>
                      <ul className="mt-2 grid gap-1">
                        {items.length > 0 ? (
                          items.map((item, ii) => {
                            const itemObj = item as UnknownRecord;
                            const itemName =
                              typeof itemObj.name === "string"
                                ? itemObj.name
                                : typeof itemObj.title === "string"
                                ? itemObj.title
                                : typeof itemObj.food_item === "string"
                                ? itemObj.food_item
                                : `Блюдо ${ii + 1}`;
                            const itemEnergy =
                              typeof itemObj.energy_kcal === "number"
                                ? itemObj.energy_kcal
                                : typeof itemObj.kcal === "number"
                                ? itemObj.kcal
                                : undefined;
                            return (
                              <li key={`${itemName}-${ii}`} className="text-sm">
                                • {itemName}
                                {typeof itemEnergy === "number" && (
                                  <span className="opacity-70"> — {Math.round(itemEnergy)} ккал</span>
                                )}
                              </li>
                            );
                          })
                        ) : (
                          <li className="text-sm opacity-60">Нет позиций</li>
                        )}
                      </ul>
                    </li>
                  );
                })}
              </ul>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
