import { useEffect, useState } from "react";
import type { components, paths } from "../../api/schema";
import { fetchJson } from "../../api/client";
import GlassCard from "../../components/GlassCard";
import { shareSignedExport, formatShareErrorMessage } from "../../lib/shareFile";
import { requestSignedLink } from "../../lib/sharedLinks";

const DEFAULT_TTL_SECONDS = 900;

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Will fall back to the legacy approach below
  }

  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}

async function downloadSignedFile(url: string, filename: string) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(anchor.href);
}

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
  const [hint, setHint] = useState<string | null>(null);
  const [lastSignedLink, setLastSignedLink] = useState<string | null>(null);

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

  const openSheetsHelp = () => {
    window.open("https://sheets.new", "_blank", "noopener,noreferrer");
    setHint(
      "В новой вкладке Google Sheets: File → Import → Insert link и вставь CSV-ссылку ниже."
    );
  };

  const copyLink = async () => {
    try {
      const link = await requestSignedLink("/api/v1/plan/week/export.csv", { ttlSeconds: DEFAULT_TTL_SECONDS });
      const ok = await copyToClipboard(link.absolute);
      setLastSignedLink(link.absolute);
      setHint(
        ok
          ? "Приватная CSV-ссылка скопирована (действует 15 минут). В Google Sheets выбери File → Import → Link."
          : `Не удалось скопировать автоматически. Скопируй вручную: ${link.absolute}`
      );
    } catch (error: any) {
      setHint(`Не удалось получить приватную ссылку: ${error?.message || "error"}`);
    }
  };

  const handleDownload = async (path: string, filename: string) => {
    try {
      const link = await requestSignedLink(path, { ttlSeconds: DEFAULT_TTL_SECONDS });
      await downloadSignedFile(link.absolute, filename);
      setLastSignedLink(link.absolute);
      setHint("Экспорт готов. Приватная ссылка действительна 15 минут.");
    } catch {
      setHint("Не удалось скачать файл. Попробуйте ещё раз.");
    }
  };

  const handleShare = async (path: string, filename: string, title: string) => {
    try {
      const link = await shareSignedExport(path, filename, title, { ttlSeconds: DEFAULT_TTL_SECONDS });
      setLastSignedLink(link.absolute);
      setHint("Поделиться готово. Приватная ссылка действительна 15 минут.");
    } catch (error: unknown) {
      setHint(formatShareErrorMessage(error, "Не удалось поделиться: произошла ошибка. Попробуйте ещё раз."));
    }
  };

  const openPrivateCsv = async () => {
    try {
      const link = await requestSignedLink("/api/v1/plan/week/export.csv", { ttlSeconds: DEFAULT_TTL_SECONDS });
      setLastSignedLink(link.absolute);
      window.open(link.absolute, "_blank", "noopener,noreferrer");
      setHint("Открыта приватная ссылка (15 минут). Можно поделиться точечно.");
    } catch {
      setHint("Не удалось открыть приватную ссылку. Попробуйте ещё раз.");
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <GlassCard tone="light" className="drop-shadow-lg" ariaLabel="Действия для недельного плана" role="region">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Мой недельный план</h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              onClick={() => handleDownload("/api/v1/plan/week/export.csv", "week_plan.csv")}
            >
              Export Week CSV
            </button>
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              onClick={() => handleDownload("/api/v1/plan/week/export.pdf", "week_plan.pdf")}
            >
              Export Week PDF
            </button>
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              aria-label="Share week plan (PDF)"
              onClick={() =>
                handleShare(
                  "/api/v1/plan/week/export.pdf",
                  "week_plan.pdf",
                  "PulsePlate — Weekly Plan"
                )
              }
            >
              Share…
            </button>
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              onClick={openSheetsHelp}
              title="Откроет пустой Google Sheets"
            >
              Open in Google Sheets
            </button>
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              onClick={copyLink}
              title="Скопировать прямую CSV-ссылку"
            >
              Copy CSV Link
            </button>
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              onClick={openPrivateCsv}
            >
              Open Private CSV
            </button>
          </div>
        </div>
        {hint && (
          <div className="mt-3 text-sm text-slate-600">
            {hint}
            {lastSignedLink && (
              <div>
                Приватная ссылка: <code>{lastSignedLink}</code>
              </div>
            )}
          </div>
        )}
      </GlassCard>
      <GlassCard className="drop-shadow-md" role="region" ariaLabel="Сводка недельного плана">
        {dailyMenus.length === 0 ? (
          <div className="opacity-80">Пока пусто.</div>
        ) : (
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
            <li
              key={dayTitle}
              className="border border-white/15 rounded-2xl bg-white/10 p-4 space-y-2 backdrop-blur-sm"
            >
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
                    <li
                      key={`${mealName}-${mi}`}
                      className="rounded-xl border border-white/10 bg-white/10 p-3 backdrop-blur-sm"
                    >
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
        )}
      </GlassCard>
    </div>
  );
}
