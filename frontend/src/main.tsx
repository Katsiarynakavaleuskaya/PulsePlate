import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./index.css";
import "./i18n";
import "wicg-inert";
import { i18nSmoke } from "./i18n/smoke";
import { apiSmoke } from "./api/smoke";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

const root = ReactDOM.createRoot(rootElement);

i18nSmoke();

if (import.meta.env.DEV) {
  // лениво импортируем, чтобы не тащить в прод
  import("./mocks/browser")
    .then(({ worker }) => {
      return worker.start({ onUnhandledRequest: "bypass" });
    })
    .then(() => {
      // Run smoke tests after MSW worker is started
      apiSmoke();
    })
    .catch((error) => {
      console.error("Failed to start MSW worker:", error);
      // Fallback: run smoke tests even if MSW fails
      apiSmoke();
    });
} else {
  // For non-DEV builds, run smoke tests immediately
  apiSmoke();
}

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
