import { useEffect, useMemo, useState } from "react";
import type { paths } from "../../api/schema";
import { fetchJson } from "../../api/client";

// RU: Тип ответа берём из OpenAPI (frontend/src/api/schema.ts).
// EN: Response type derived from OpenAPI schema.
type SearchResp =
  paths["/api/v1/foods/search"]["get"]["responses"]["200"]["content"]["application/json"];

type FoodHit = SearchResp extends Array<infer Item> ? Item : never;

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
        const url = `/api/v1/foods/search?query=${encodeURIComponent(value)}&limit=10`;
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

  const items: FoodHit[] = Array.isArray(data) ? data : [];

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
        {items.map((p) => (
          <li key={p.id} className="border rounded-2xl p-3">
            <div className="font-medium">{p.name}</div>
            <div className="text-sm opacity-70">Энергия: {p.kcal} ккал / 100 г</div>
            <div className="text-xs opacity-60">
              Б / Ж / У: {p.protein_g} / {p.fat_g} / {p.carbs_g} (г на 100 г)
            </div>
          </li>
        ))}
        {!loading && !err && q && items.length === 0 && (
          <li className="opacity-70">Ничего не найдено.</li>
        )}
      </ul>
    </div>
  );
}
