import type { Preview } from "@storybook/react";
import "../src/index.css";

// Mock i18next for stories
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

export const setupI18nForStorybook = () => {
  i18n
    .use(initReactI18next)
    .init({
      lng: "en",
      fallbackLng: "en",
      debug: false,
      interpolation: {
        escapeValue: false,
      },
      resources: {
        en: {
          translation: {
            nutrition: {
              water: {
                title: "Daily Water Intake",
                subtitle: "Stay hydrated for optimal health",
              },
              micros: {
                unavailable: "Micronutrient targets not available",
              },
            },
          },
        },
      },
    });
};

setupI18nForStorybook();

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    docs: {
      toc: true,
    },
  },
};

export default preview;
