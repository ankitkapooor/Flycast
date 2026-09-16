import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F4F1EA",
        foreground: "#1A1A18",
        paper: {
          light: "#FAF8F5",
          DEFAULT: "#F4F1EA",
          dark: "#EAE6DC",
          border: "#DCD6C8",
        },
        fly: {
          DEFAULT: "#C2410C", // terracotta / scientific orange
          hover: "#9A3412",
          light: "#FFF7ED",
          border: "#FDBA74",
        },
        obs: {
          actual: "#1A1A18",
          persistence: "#64748B",
          autoregressive: "#0D9488",
          control: "#854D0E",
        },
        console: {
          bg: "#181816",
          text: "#E5E5DF",
          border: "#2C2C28",
          muted: "#888882",
        }
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "'Segoe UI'", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "'Liberation Mono'", "monospace"],
      },
      borderWidth: {
        '1': '1px',
      }
    },
  },
  plugins: [],
};
export default config;
