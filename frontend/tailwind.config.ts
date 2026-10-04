import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#0d1117",
          panel: "#13151f",
          raised: "#1a1a2e",
        },
        border: {
          DEFAULT: "#2a2d3a",
        },
        accent: {
          yellow: "#ecad0a",
          blue: "#209dd7",
          purple: "#753991",
        },
        up: "#2ecc71",
        down: "#e5484d",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      keyframes: {
        "flash-up": {
          "0%": { backgroundColor: "rgba(46, 204, 113, 0.35)" },
          "100%": { backgroundColor: "transparent" },
        },
        "flash-down": {
          "0%": { backgroundColor: "rgba(229, 72, 77, 0.35)" },
          "100%": { backgroundColor: "transparent" },
        },
      },
      animation: {
        "flash-up": "flash-up 600ms ease-out",
        "flash-down": "flash-down 600ms ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
