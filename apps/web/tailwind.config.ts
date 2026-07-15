import type { Config } from "tailwindcss";

const config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        indigo: "var(--indigo)",
        "indigo-soft": "var(--indigo-soft)",
        success: "var(--green)",
        warning: "var(--amber)",
        danger: "var(--red)",
      },
    },
  },
  plugins: [],
} satisfies Config;

export default config;
