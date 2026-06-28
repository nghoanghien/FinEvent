import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";
import { colorRgb, colors } from "./src/shared/constants/design-tokens";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        anton: ["var(--font-anton)", "sans-serif"],
      },
      colors: {
        primary: `rgb(${colorRgb.primary} / <alpha-value>)`,
        secondary: `rgb(${colorRgb.secondary} / <alpha-value>)`,
        warning: `rgb(${colorRgb.warning} / <alpha-value>)`,
        danger: `rgb(${colorRgb.danger} / <alpha-value>)`,
        background: "var(--background)",
        foreground: "var(--foreground)",
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
        finevent: "0 8px 40px rgba(0, 0, 0, 0.04)",
        "finevent-hover": "0 18px 55px rgba(0, 0, 0, 0.10)",
      },
      keyframes: {
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-1000px 0" },
          "100%": { backgroundPosition: "1000px 0" },
        },
        pulseBorder: {
          "0%, 100%": { borderColor: `rgba(${colorRgb.primary}, 0.3)` },
          "50%": { borderColor: `rgba(${colorRgb.primary}, 0.8)` },
        },
      },
      animation: {
        "fade-in-up": "fadeInUp 0.55s ease-out",
        shimmer: "shimmer 2s linear infinite",
        "pulse-border": "pulseBorder 2s ease-in-out infinite",
      },
    },
  },
  plugins: [
    typography,
    ({ addBase }: { addBase: (base: Record<string, Record<string, string>>) => void }) => {
      addBase({
        ":root": {
          "--primary": colors.primary,
          "--secondary": colors.secondary,
          "--warning": colors.warning,
          "--danger": colors.danger,
          "--primary-rgb": colorRgb.primary,
          "--secondary-rgb": colorRgb.secondary,
          "--warning-rgb": colorRgb.warning,
          "--danger-rgb": colorRgb.danger,
        },
      });
    },
  ],
};

export default config;
