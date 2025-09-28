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

const renderApp = () => {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
};

if (import.meta.env.DEV) {
  // лениво импортируем, чтобы не тащить в прод
  import("./mocks/browser")
    .then(({ worker }) => {
      return worker.start({ onUnhandledRequest: "bypass" });
    })
    .then(() => {
      apiSmoke();
      renderApp();
    })
    .catch((error) => {
      console.error("Failed to start MSW worker:", error);
      apiSmoke();
      renderApp();
    });
} else {
  // For non-DEV builds, run smoke tests immediately
  apiSmoke();
  renderApp();
}
