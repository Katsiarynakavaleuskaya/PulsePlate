import React from "react";
import ReactDOM from "react-dom/client";
import WeeklyPlanViewer from "./features/plan/WeeklyPlanViewer";
import ShoplistPreview from "./features/shoplist/ShoplistPreview";
import "./styles/tokens.css";
import "./index.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <main style={{ display: "grid", gap: "2rem", padding: "1.5rem" }}>
      <section>
        <WeeklyPlanViewer />
      </section>
      <section>
        <ShoplistPreview />
      </section>
    </main>
  </React.StrictMode>,
);
