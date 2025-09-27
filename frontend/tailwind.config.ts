// RU: Подхватываем CSS-переменные как Tailwind-цвета и радиусы.
// EN: Map CSS variables into Tailwind theme.

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "var(--pp-navy)",
        primary: "var(--pp-primary)",
        gold: "var(--pp-gold)",
        accent: "var(--pp-accent)",
        text: "var(--pp-text)",
        muted: "var(--pp-muted)",
      },
      borderRadius: {
        xl: "var(--pp-radius-xl)",
      },
    },
  },
  plugins: [],
};
