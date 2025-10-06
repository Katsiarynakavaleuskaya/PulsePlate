// RU: Подхватываем CSS-переменные как Tailwind-цвета и радиусы.
// EN: Map CSS variables into Tailwind theme.
const config = {
    content: [
        "./index.html", // actual Vite entry HTML
        "./src/**/*.{ts,tsx}",
    ],
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
export default config;
