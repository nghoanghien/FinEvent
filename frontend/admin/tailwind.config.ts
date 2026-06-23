import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
        },
        ink: {
          900: "#111827",
          700: "#374151",
          500: "#6b7280",
        },
      },
      boxShadow: {
        panel: "0 1px 2px rgba(15, 23, 42, 0.05), 0 10px 30px rgba(15, 23, 42, 0.04)",
      },
    },
  },
  plugins: [typography],
};

export default config;
