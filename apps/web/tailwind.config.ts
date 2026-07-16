import type { Config } from "tailwindcss";

const config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f8fafc",
        ink: "#0f172a",
        muted: "#64748b",
        "indigo-soft": "#eef2ff",
        success: "#047857",
        warning: "#a16207",
        danger: "#b91c1c",
      },
    },
  },
  plugins: [],
} satisfies Config;

export default config;
