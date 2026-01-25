import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchJson, fetchBlob } from "../../api/client";
import { shareSignedExport, formatShareErrorMessage } from "../../lib/shareFile";
import GlassCard from "../../components/GlassCard";

/**
 * Represents a single shopping list item with optional properties
 */
type ShopItem = {
  /** Unique identifier for the item */
  id?: string;
  /** Name of the shopping item */
  name?: string;
  /** Quantity of the item */
  qty?: number;
  /** Unit of measurement (e.g., "kg", "pcs") */
  unit?: string;
  /** Store aisle where item is located */
  aisle?: string;
  /** Store name */
  store?: string;
  /** Additional notes for the item */
  note?: string;
};

/**
 * Represents a group of shopping items organized by aisle
 */
type ShopGroup = {
  /** Aisle name for the group */
  aisle?: string;
  /** Array of items in this group */
  items?: ShopItem[];
};

/**
 * Complete shopping list data structure
 */
type Shoplist = {
  /** Store name */
  store?: string;
  /** Currency for price display */
  currency?: string;
  /** Estimated total cost */
  total_estimated?: number;
  /** Groups organized by aisles */
  groups?: ShopGroup[];
  /** Flat list of all items (alternative to groups) */
  items?: ShopItem[];
};

/**
 * Shopping list preview component that displays user's shopping list with export and share options
 *
 * Features:
 * - Loads shopping list data from API
 * - Displays items organized by store aisles
 * - Provides CSV and PDF export functionality
 * - Includes sharing capabilities
 * - Shows loading states and error handling
 * - Fully localized interface (Russian primary)
 *
 * @returns React component for shopping list management
 */
export default function ShoplistPreview() {
  const { t } = useTranslation();

  const [data, setData] = useState<Shoplist | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"csv" | "pdf" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const cleanupRef = useRef<Array<{ id: number; cleanup: () => void }>>([]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const res = await fetchJson<Shoplist>("/api/v1/shoplist");
        setData(res);
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : "Fetch error");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    return () => {
      cleanupRef.current.forEach(({ id, cleanup }) => {
        cleanup(); // Execute cleanup first to remove DOM nodes and revoke URLs
        clearTimeout(id); // Then clear the timeout to prevent any potential firing
      });
      cleanupRef.current = [];
    };
  }, []);

  /**
   * Downloads a file of specified type (CSV or PDF) by creating a blob URL and anchor element
   * Uses fetchBlob() for thin-client compliance (no direct fetch outside client.ts)
   *
   * @param kind - File type to download ("csv" or "pdf")
   * @throws Error if fetch fails or response is not ok
   */
  const downloadFile = useCallback(async (kind: "csv" | "pdf") => {
    const filename = `shoplist.${kind}`;
    const blob = await fetchBlob(`/api/v1/shoplist/export.${kind}`);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();

    // Remove anchor synchronously - it's not needed after click
    anchor.remove();

    // Schedule URL revocation with a reasonable timeout
    // The browser will initiate download before this fires
    const revokeTimeout = setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 1000);

    cleanupRef.current.push({
      id: revokeTimeout as any,
      cleanup: () => URL.revokeObjectURL(url)
    });
  }, []);

  const handleDownload = useCallback(async (kind: "csv" | "pdf") => {
    try {
      setDownloading(kind);
      await downloadFile(kind);
    } catch (error: unknown) {
      setDownloadError(formatShareErrorMessage(error, `${t('shoplist.downloadError')}: ${error instanceof Error ? error.message : t('shoplist.tryAgain')}`));
    } finally {
      setDownloading(null);
    }
  }, [downloadFile, t]);

  const handleShare = useCallback(async (kind: "csv" | "pdf") => {
    try {
      const filename = kind === "csv" ? "shoplist.csv" : "shoplist.pdf";
      await shareSignedExport(`/api/v1/shoplist/export.${kind}`, filename, "PulsePlate — Shopping List");
    } catch (error: unknown) {
      setDownloadError(formatShareErrorMessage(error, `${t('shoplist.shareError')}. ${t('shoplist.tryAgain')}`));
    }
  }, [t]);

  if (loading) {
    return <div className="max-w-3xl mx-auto p-6">{t('shoplist.loading')}</div>;
  }

  if (err) {
    return (
      <div className="max-w-3xl mx-auto p-6 text-red-600">
        {t('shoplist.error')}: {err}
      </div>
    );
  }

  if (!data) {
    return <div className="max-w-3xl mx-auto p-6 opacity-70">{t('shoplist.empty')}</div>;
  }

  const groups = data.groups && data.groups.length > 0
    ? data.groups
    : [{ aisle: "All items", items: data.items ?? [] }];

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <GlassCard
        tone="light"
        role="region"
        ariaLabelledBy="shopping-actions-title"
        contentClassName="space-y-3"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="shopping-actions-title" className="text-xl font-semibold">
            {t('shoplist.title')}
          </h2>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="opacity-80 text-slate-700">
              {data.store ? `${t('shoplist.store')}: ${data.store}` : ""}
              {typeof data.total_estimated === "number" && (
                <>
                  {data.store ? " • " : ""}{t('shoplist.estimated')} {data.total_estimated}
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
                {downloading === "csv" ? t('shoplist.downloadingCsv') : t('shoplist.downloadCsv')}
              </button>
              <button
                type="button"
                onClick={() => handleDownload("pdf")}
                disabled={downloading === "pdf"}
                className="border rounded-xl px-3 py-2 text-sm"
              >
                {downloading === "pdf" ? t('shoplist.downloadingPdf') : t('shoplist.downloadPdf')}
              </button>
              <button
                type="button"
                onClick={() => handleShare("pdf")}
                className="border rounded-xl px-3 py-2 text-sm"
                aria-label={`${t('shoplist.share')} ${t('shoplist.downloadPdf')}`}
              >
                {t('shoplist.share')}
              </button>
            </div>
          </div>
        </div>
        {downloadError && (
          <div className="text-sm text-red-500" role="status" aria-live="polite">
            {downloadError}
          </div>
        )}
      </GlassCard>
      <GlassCard
        role="region"
        ariaLabelledBy="shopping-content-title"
        contentClassName="space-y-4"
      >
        <h2 id="shopping-content-title" className="text-lg font-semibold">
          {t('shoplist.contentTitle')}
        </h2>
        <ul className="space-y-3">
          {groups.map((group, gi) => (
            <li
              key={group.aisle ?? gi}
              className="border border-white/15 rounded-2xl bg-white/5 p-4 backdrop-blur-sm"
            >
              <div className="font-medium">{group.aisle ?? t('shoplist.category')}</div>
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
                  <li className="text-sm opacity-60">{t('shoplist.noItems')}</li>
                )}
              </ul>
            </li>
          ))}
        </ul>
      </GlassCard>
    </div>
  );
}
