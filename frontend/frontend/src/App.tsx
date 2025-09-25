import { useState } from "react";
import ProductSearch from "./features/products/ProductSearch";
import WeeklyPlanViewer from "./features/plan/WeeklyPlanViewer";

export default function App() {
  const [tab, setTab] = useState<"week" | "search">("week");

  return (
    <div style={{ maxWidth: 980, margin: "40px auto", padding: 16 }}>
      <h1>PulsePlate — Dev</h1>
      <div style={{ display: "flex", gap: 8, margin: "12px 0" }}>
        <button
          type="button"
          onClick={() => setTab("week")}
          style={{
            padding: "8px 16px",
            borderRadius: 16,
            border: tab === "week" ? "2px solid #2563eb" : "1px solid #cbd5f5",
            background: tab === "week" ? "#2563eb" : "transparent",
            color: tab === "week" ? "#fff" : "inherit",
            cursor: "pointer",
          }}
        >
          Weekly Plan
        </button>
        <button
          type="button"
          onClick={() => setTab("search")}
          style={{
            padding: "8px 16px",
            borderRadius: 16,
            border: tab === "search" ? "2px solid #2563eb" : "1px solid #cbd5f5",
            background: tab === "search" ? "#2563eb" : "transparent",
            color: tab === "search" ? "#fff" : "inherit",
            cursor: "pointer",
          }}
        >
          Product Search
        </button>
      </div>
      {tab === "week" ? <WeeklyPlanViewer /> : <ProductSearch />}
    </div>
  );
}
