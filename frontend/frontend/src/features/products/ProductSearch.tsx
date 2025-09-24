import { useEffect, useMemo, useState } from "react";
import type { paths } from "../../api/schema";
import { fetchJson } from "../../api/client";

// RU: Тип ответа берём из OpenAPI (frontend/src/api/schema.ts).
// EN: We derive response type from OpenAPI schema.
type SearchResp =
  paths["/api/products/search"]["get"]["responses"]["200"]["content"]["application/json"];

export default function ProductSearch() {
  const [q, setQ] = useState("");
  const [data, setData] = useState<SearchResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const debounced = useMemo(() => {
    let t: number | undefined;
    return (value: string, cb: (s: string) => void) => {
      window.clearTimeout(t);
      t = window.setTimeout(() => cb(value), 300);
    };
  }, []);

  useEffect(() => {
    if (!q) {
      setData(null);
      setErr(null);
      return;
    }
    setLoading(true);
    setErr(null);

    debounced(q, async (value) => {
      try {
        const url = `/api/products/search?q=${encodeURIComponent(value)}&limit=10`;
        const res = await fetchJson<SearchResp>(url);
        setData(res);
      } catch (e: any) {
        setErr(e?.message || "Fetch error");
        setData(null);
      } finally {
        setLoading(false);
      }
    });
  }, [q, debounced]);

  const items = (data && (data as any).items) || [];

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h2 className="text-xl font-semibold">Поиск продуктов</h2>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Введите продукт (например, yogurt)…"
        className="w-full border rounded-2xl p-3"
      />
      {loading && <div>Ищем…</div>}
      {err && <div className="text-red-600">Ошибка: {err}</div>}
      <ul className="grid gap-3">
        {items.map((p: any) => (
          <li key={p.id ?? `${p.name}-${p.brand ?? ""}`} className="border rounded-2xl p-3">
            <div className="font-medium">{p.name}</div>
            {p.brand && <div className="text-sm opacity-70">{p.brand}</div>}
            {p.energy_kcal != null && (
              <div className="text-sm">Энергия: {p.energy_kcal} ккал / 100 г</div>
            )}
          </li>
        ))}
        {!loading && !err && q && items.length === 0 && (
          <li className="opacity-70">Ничего не найдено.</li>
        )}
      </ul>
    </div>
  );
}
