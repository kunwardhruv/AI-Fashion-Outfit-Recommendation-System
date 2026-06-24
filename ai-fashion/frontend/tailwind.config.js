/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        gold: {
          400: "#d4af37",
          500: "#b8971f",
        },
        fashion: {
          dark: "#0a0a0f",
          card: "#131320",
          border: "#2a2a3d",
          muted: "#6b6b8a",
        },
      },
      fontFamily: {
        display: ["'Playfair Display'", "serif"],
        body: ["'Inter'", "sans-serif"],
      },
    },
  },
  plugins: [],
};
