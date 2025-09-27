import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./index.css";
import "./i18n";
import { i18nSmoke } from "./i18n/smoke";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

const root = ReactDOM.createRoot(rootElement);

i18nSmoke();

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
