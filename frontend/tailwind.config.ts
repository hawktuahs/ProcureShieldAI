import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "gov-blue": "#1e3a5f",
        "gov-blue-light": "#2d5a9e",
        pass: "#22C55E",
        fail: "#EF4444",
        review: "#F59E0B",
        override: "#3B82F6",
      },
    },
  },
  plugins: [],
};
export default config;
