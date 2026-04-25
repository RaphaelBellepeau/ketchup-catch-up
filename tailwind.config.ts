import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  safelist: [
    "bg-ketchup-red",
    "bg-coral",
    "bg-navy",
    "bg-charcoal",
    "bg-cream",
    "bg-mint",
    "bg-sky",
    "bg-lavender",
    "bg-sunshine",
    "bg-blush",
    "bg-light-gray",
    "bg-slate",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        h1: ["26px", { lineHeight: "1.2", fontWeight: "500" }],
        h2: ["20px", { lineHeight: "1.3", fontWeight: "500" }],
        h3: ["15px", { lineHeight: "1.4", fontWeight: "500" }],
        body: ["13px", { lineHeight: "1.5", fontWeight: "400" }],
        meta: ["11px", { lineHeight: "1.4", fontWeight: "500", letterSpacing: "0.08em" }],
      },
      colors: {
        // Ketchup brand palette
        "ketchup-red": "#FF4B4B",
        coral: "#FF7A59",
        navy: "#0D1B2A",
        charcoal: "#1F2937",
        cream: "#FFF3E0",
        mint: "#B6EAD7",
        sky: "#E0F2FE",
        lavender: "#E9D5FF",
        sunshine: "#FFD166",
        blush: "#FFE1E6",
        "light-gray": "#E5E7EB",
        slate: "#6B7280",

        // Shadcn semantic tokens
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      borderRadius: {
        card: "16px",
        btn: "14px",
        field: "12px",
        pill: "999px",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "waveform-pulse": {
          "0%, 100%": { transform: "scaleY(0.3)" },
          "50%": { transform: "scaleY(1)" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "check-pop": {
          "0%": { transform: "scale(0)" },
          "60%": { transform: "scale(1.1)" },
          "100%": { transform: "scale(1)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "waveform-pulse": "waveform-pulse 1s ease-in-out infinite",
        "fade-in": "fade-in 0.4s ease-out both",
        "check-pop": "check-pop 0.6s ease-out both",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
