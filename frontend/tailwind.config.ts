import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#050608",
        panel: "#0a0d12",
        panelSoft: "#0f1318",
        accent: "#10b981",        /* emerald-500 — vivid green */
        accentLight: "#34d399",   /* emerald-400 */
        accentStrong: "#059669",  /* emerald-600 */
        userBubble: "#0d2b20",
        assistantBubble: "#090d14",
        borderSoft: "rgba(255,255,255,0.07)",
        thinkingGreen: "#10b981"
      },
      boxShadow: {
        glow: "0 20px 45px rgba(0, 0, 0, 0.35)",
        bubble: "0 18px 38px rgba(0, 0, 0, 0.28)"
      },
      animation: {
        "fade-in-up": "fadeInUp 0.35s ease-out",
        shimmer: "shimmer 2.15s linear infinite",
        flicker: "flicker 1s step-start infinite"
      },
      keyframes: {
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" }
        },
        flicker: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" }
        }
      }
    }
  },
  plugins: []
};

export default config;