import { useCallback, useEffect, useState } from "react";
import { fetchJson } from "../../api/client";
import { shareSignedExport, formatShareErrorMessage } from "../../lib/shareFile";
import GlassCard from "../../components/GlassCard";

type ShopItem = {
  id?: string;
  name?: string;
  qty?: number;
  unit?: string;
  aisle?: string;
  store?: string;
  note?: string;
};

type ShopGroup = {
  aisle?: string;
  items?: ShopItem[];
};

type Shoplist = {
  store?: string;
  currency?: string;
  total_estimated?: number;
  groups?: ShopGroup[];
  items?: ShopItem[];
};

/**
 * Renders a preview of the current shopping list with actions to export or share it.
 *
 * Displays loading and error states, fetches the list on mount, groups items by aisle when available,
 * and provides buttons to download the list as CSV or PDF and to share the PDF.
 *
 * @returns The component's rendered JSX element representing the shopping list preview and controls.
 */
export default function ShoplistPreview() {
  const [data, setData] = useState<Shoplist | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"csv" | "pdf" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const res = await fetchJson<Shoplist>("/api/v1/shoplist");
        setData(res);
      } catch (e: any) {
        setErr(e?.message || "Fetch error");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const downloadFile = useCallback(async (kind: "csv" | "pdf") => {
    const filename = `shoplist.${kind}`;
    const res = await fetch(`/api/v1/shoplist/export.${kind}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }, []);

  const handleDownload = useCallback(
    async (kind: "csv" | "pdf") => {
      try {
        setDownloadError(null);
        setDownloading(kind);
        await downloadFile(kind);
      } catch {
        setDownloadError("Не удалось скачать файл. Попробуйте ещё раз.");
      } finally {
        setDownloading(null);
      }
    },
    [downloadFile],
  );

  const handleShare = useCallback(
    async (kind: "csv" | "pdf") => {
      try {
        setDownloadError(null);
        const filename = kind === "csv" ? "shoplist.csv" : "shoplist.pdf";
        await shareSignedExport(`/api/v1/shoplist/export.${kind}`, filename, "PulsePlate — Shopping List");
      } catch (error: unknown) {
        setDownloadError(formatShareErrorMessage(error, "Не удалось поделиться файлом. Попробуйте ещё раз."));
      }
    },
    [],
  );

  if (loading) {
    return <div className="max-w-3xl mx-auto p-6">Загружаем список…</div>;
  }

  if (err) {
    return (
      <div className="max-w-3xl mx-auto p-6 text-red-600">
        Ошибка: {err}
      </div>
    );
  }

  if (!data) {
    return <div className="max-w-3xl mx-auto p-6 opacity-70">Пусто.</div>;
  }

  const groups = data.groups && data.groups.length > 0
    ? data.groups
    : [{ aisle: "All items", items: data.items ?? [] }];

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <GlassCard tone="light" className="drop-shadow-lg" role="region" ariaLabel="Действия для списка покупок">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Список покупок</h2>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="opacity-80 text-slate-700">
              {data.store ? `Магазин: ${data.store}` : ""}
              {typeof data.total_estimated === "number" && (
                <>
                  {data.store ? " • " : ""}≈ {data.total_estimated}
                  {data.currency ? ` ${data.currency}` : ""}
                </>
              )}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleDownload("csv")}
                disabled={downloading === "csv"}
                className="border rounded-xl px-3 py-2 text-sm"
              >
                {downloading === "csv" ? "Скачиваем CSV…" : "Export CSV"}
              </button>
              <button
                type="button"
                onClick={() => handleDownload("pdf")}
                disabled={downloading === "pdf"}
                className="border rounded-xl px-3 py-2 text-sm"
              >
                {downloading === "pdf" ? "Скачиваем PDF…" : "Export PDF"}
              </button>
              <button
                type="button"
                onClick={() => handleShare("pdf")}
                className="border rounded-xl px-3 py-2 text-sm"
                aria-label="Share shopping list PDF"
              >
                Share…
              </button>
            </div>
          </div>
        </div>
        {downloadError && (
          <div className="mt-3 text-sm text-red-500">Ошибка загрузки: {downloadError}</div>
        )}
      </GlassCard>
      <GlassCard className="drop-shadow-md" role="region" ariaLabel="Содержимое списка покупок">
        <ul className="space-y-3">
          {groups.map((group, gi) => (
            <li
              key={group.aisle ?? gi}
              className="border border-white/15 rounded-2xl bg-white/5 p-4 backdrop-blur-sm"
            >
              <div className="font-medium">{group.aisle ?? "Категория"}</div>
              <ul className="mt-2 grid gap-1">
                {(group.items ?? []).map((item, ii) => (
                  <li key={item.id ?? `${item.name}-${ii}`} className="text-sm">
                    • {item.name ?? "—"}
                    {typeof item.qty === "number" && (
                      <span>
                        {" "}— {item.qty}
                        {item.unit ? ` ${item.unit}` : ""}
                      </span>
                    )}
                    {item.note && <span className="opacity-60"> ({item.note})</span>}
                  </li>
                ))}
                {(!group.items || group.items.length === 0) && (
                  <li className="text-sm opacity-60">Нет позиций</li>
                )}
              </ul>
            </li>
          ))}
        </ul>
      </GlassCard>
    </div>
  );
}