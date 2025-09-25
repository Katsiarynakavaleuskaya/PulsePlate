import { useEffect, useState } from "react";
import { fetchJson } from "../../api/client";

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

export default function ShoplistPreview() {
  const [data, setData] = useState<Shoplist | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

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
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Список покупок</h2>
        <div className="text-sm opacity-70">
          {data.store ? `Магазин: ${data.store}` : ""}
          {typeof data.total_estimated === "number" && (
            <span>
              {data.store ? " • " : ""}≈ {data.total_estimated}
              {data.currency ? ` ${data.currency}` : ""}
            </span>
          )}
        </div>
      </div>
      <ul className="space-y-3">
        {groups.map((group, gi) => (
          <li key={group.aisle ?? gi} className="border rounded-2xl p-4">
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
    </div>
  );
}
