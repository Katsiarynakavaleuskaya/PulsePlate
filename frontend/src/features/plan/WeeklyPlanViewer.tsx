import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ProWeekPlanRequest } from "../../api/premium/weekly-plan";
import { fetchBlob } from "../../api/client";
import GlassCard from "../../components/GlassCard";
import { shareSignedExport, formatShareErrorMessage } from "../../lib/shareFile";
import { requestSignedLink } from "../../lib/sharedLinks";
import { getClientLocale } from "../../lib/i18n";
import { useWeeklyPlan } from "../weekly-plan/hooks/useWeeklyPlan";
import type { Meal } from "../weekly-plan/model/types";

const DEFAULT_TTL_SECONDS = 900;

async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (error) {
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

/**
 * Downloads a file from signed URL using thin HTTP adapter
 * Uses fetchBlob() for thin-client compliance (external signed URL, no auth headers)
 */
async function downloadSignedFile(url: string, filename: string): Promise<void> {
  const blob = await fetchBlob(url);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Delay revocation to ensure download starts
  // Delay revocation to ensure download completes (consistent with ShoplistPreview)
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

const DEFAULT_REQUEST: ProWeekPlanRequest = {
  sex: "female",
  age: 30,
  height_cm: 168,
  weight_kg: 62,
  activity: "moderate",
  goal: "maintain",
  diet_flags: [],
  lang: "en",
};

function getDayTitle(index: number, t: (key: string, options?: Record<string, unknown>) => string): string {
  return t("plan.day_fallback", { number: index + 1 });
}

function getMealName(meal: Meal): string {
  return meal.title_translated || meal.title;
}

function formatMetricLabel(key: string): string {
  return key.replace(/_/g, " ");
}

function getMealDetails(meal: Meal): string[] {
  const grams = Object.entries(meal.grams).slice(0, 2).map(
    ([label, value]) => `${formatMetricLabel(label)}: ${Math.round(value)} g`
  );

  if (grams.length > 0) {
    return grams;
  }

  return Object.entries(meal.macros).slice(0, 2).map(
    ([label, value]) => `${formatMetricLabel(label)}: ${Math.round(value)}`
  );
}

export default function WeeklyPlanViewer() {
  const { t } = useTranslation();
  const [hint, setHint] = useState<string | null>(null);
  const [lastSignedLink, setLastSignedLink] = useState<string | null>(null);
  const [request, setRequest] = useState<ProWeekPlanRequest | null>(null);

  useEffect(() => {
    const locale = getClientLocale() as ProWeekPlanRequest["lang"];
    const supportedLangs: ProWeekPlanRequest["lang"][] = ["en", "ru", "es"];
    setRequest({
      ...DEFAULT_REQUEST,
      lang: supportedLangs.includes(locale) ? locale : "en",
    });
  }, []);

  const { data, loading, error: err } = useWeeklyPlan({
    targets: request,
    enabled: request !== null,
  });

  if (loading) {
    return <div className="max-w-3xl mx-auto p-6">{t('plan.loadingWeek')}</div>;
  }

  if (err) {
    return (
      <div className="max-w-3xl mx-auto p-6 text-red-600">
        {t('plan.loadError')}: {err}
      </div>
    );
  }

  const dailyMenus = data?.days ?? [];

  const openSheetsHelp = () => {
    window.open("https://sheets.new", "_blank", "noopener,noreferrer");
    setHint(t('plan.sheetsHelp'));
  };

  const copyLink = async () => {
    try {
      const link = await requestSignedLink("/api/v1/plan/week/export.csv", { ttlSeconds: DEFAULT_TTL_SECONDS });
      const ok = await copyToClipboard(link.absolute);
      setLastSignedLink(link.absolute);
      setHint(
        ok
          ? t('plan.linkCopied')
          : `${t('plan.copyFailed')}: ${link.absolute}`
      );
    } catch (error: any) {
      setHint(`${t('plan.linkRequestFailed')}: ${error?.message || t('plan.unknownError')}`);
    }
  };

  const handleDownload = async (path: string, filename: string) => {
    try {
      const link = await requestSignedLink(path, { ttlSeconds: DEFAULT_TTL_SECONDS });
      await downloadSignedFile(link.absolute, filename);
      setLastSignedLink(link.absolute);
      setHint(t('plan.exportReady'));
    } catch (error: any) {
      setHint(`${t('plan.downloadFailed')}: ${error?.message || t('plan.unknownError')}. ${t('plan.tryAgain')}`);
    }
  };

  const handleShare = async (path: string, filename: string, title: string) => {
    try {
      const link = await shareSignedExport(path, filename, title, { ttlSeconds: DEFAULT_TTL_SECONDS });
      setLastSignedLink(link.absolute);
      setHint(t('plan.shareReady'));
    } catch (error: any) {
      setHint(formatShareErrorMessage(error, `${t('plan.shareFailed')}. ${t('plan.tryAgain')}`));
    }
  };

  const openPrivateCsv = async () => {
    try {
      const link = await requestSignedLink("/api/v1/plan/week/export.csv", { ttlSeconds: DEFAULT_TTL_SECONDS });
      setLastSignedLink(link.absolute);
      window.open(link.absolute, "_blank", "noopener,noreferrer");
      setHint(t('plan.linkOpened'));
    } catch (error: any) {
      setHint(`${t('plan.linkOpenFailed')}: ${error?.message || t('plan.unknownError')}. ${t('plan.tryAgain')}`);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <GlassCard
        tone="light"
        ariaLabelledBy="weekly-plan-actions-title"
        role="region"
        contentClassName="space-y-3"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="weekly-plan-actions-title" className="text-xl font-semibold">
            {t('plan.weeklyPlanTitle')}
          </h2>
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
              title={t('plan.openSheetsTitle')}
            >
              Open in Google Sheets
            </button>
            <button
              type="button"
              className="border rounded-xl px-3 py-2 text-sm"
              onClick={copyLink}
              title={t('plan.copyCsvLinkTitle')}
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
          <div className="mt-3 text-sm text-slate-700" role="status" aria-live="polite">
            {hint}
            {lastSignedLink && (
              <div>
                {t('plan.privateLinkLabel')}: <code>{lastSignedLink}</code>
              </div>
            )}
          </div>
        )}
      </GlassCard>
      <GlassCard
        role="region"
        ariaLabelledBy="weekly-plan-summary-title"
        contentClassName="space-y-3"
      >
        <h2 id="weekly-plan-summary-title" className="text-lg font-semibold">
          {t('plan.weeklySummaryTitle')}
        </h2>
        {dailyMenus.length === 0 ? (
          <div className="opacity-80">{t('plan.emptySummary')}</div>
        ) : (
          <ul className="space-y-4">
            {dailyMenus.map((menu, idx) => {
              const dayTitle = menu.dayName || getDayTitle(idx, t);
              const dayEnergy = menu.kcal;
              const meals = menu.meals;

              return (
                <li
                  key={`${dayTitle}-${idx}`}
                  className="border border-white/15 rounded-2xl bg-white/10 p-4 space-y-2 backdrop-blur-sm"
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium">{dayTitle}</div>
                    {typeof dayEnergy === "number" && (
                      <div className="text-sm opacity-70">{Math.round(dayEnergy)} {t('plan.kcalPerDay')}</div>
                    )}
                  </div>
                  <ul className="space-y-2">
                    {meals.map((meal, mi) => {
                      const mealName = getMealName(meal);
                      const items = getMealDetails(meal);

                      return (
                        <li
                          key={`${mealName}-${mi}`}
                          className="rounded-xl border border-white/10 bg-white/10 p-3 backdrop-blur-sm"
                        >
                          <div className="flex items-center justify-between">
                            <div className="font-medium">{mealName}</div>
                            <div className="text-sm opacity-70">{Math.round(meal.kcal)} {t('plan.kcal')}</div>
                          </div>
                          <ul className="mt-2 grid gap-1">
                            {items.length > 0 ? (
                              items.map((item, ii) => (
                                <li key={`${mealName}-${ii}`} className="text-sm">
                                  • {item}
                                </li>
                              ))
                            ) : (
                              <li className="text-sm opacity-60">{t('plan.noItems')}</li>
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
