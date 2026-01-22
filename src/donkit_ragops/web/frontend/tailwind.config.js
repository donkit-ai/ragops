/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme base colors (matching Figma design)
        dark: {
          bg: '#0a0a0a',       // Very dark background
          surface: '#1a1a1a',  // Card/surface background
          input: '#222529',    // Input field background (from Figma)
          border: '#2a2a2a',   // Borders
          'border-input': '#888E95', // Input field border (from Figma)
          hover: '#242424',    // Hover states
          text: {
            primary: '#ffffff',
            secondary: '#a0a0a0',
            muted: '#666666',
          }
        },
        // Accent colors
        accent: {
          red: {
            DEFAULT: '#EA6464',
            hover: '#d84545',
            light: '#f28b8b',
          },
          green: {
            DEFAULT: '#10b981',
            hover: '#059669',
            light: '#6ee7b7',
          },
          orange: {
            DEFAULT: '#f97316',
            hover: '#ea580c',
            light: '#fdba74',
          },
          blue: {
            DEFAULT: '#3b82f6',
            hover: '#2563eb',
            light: '#93c5fd',
          }
        },
        // Status colors (for badges)
        status: {
          done: '#10b981',
          failed: '#ef4444',
          pending: '#3b82f6',
          running: '#f97316',
        }
      },
    },
  },
  plugins: [],
}
