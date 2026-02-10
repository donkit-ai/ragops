/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme base colors – now powered by CSS variables from global design tokens
        dark: {
          // Semantic background colors
          bg: 'var(--color-bg)',
          surface: 'var(--color-action-item-selected)',
          input: 'transparent',
          // Borders
          border: 'var(--color-border)',
          'border-input': 'var(--color-border-hover)',
          // Hover states
          hover: 'var(--color-action-item-hover)',
          text: {
            primary: 'var(--color-txt-icon-1)',
            secondary: 'var(--color-txt-icon-2)',
            muted: 'var(--color-txt-icon-2)',
          }
        },
        // Accent colors
        accent: {
          red: {
            DEFAULT: 'var(--color-accent)',
            hover: 'var(--color-accent-hover)',
            light: 'var(--color-accent-hover)',
          },
          green: {
            DEFAULT: 'var(--color-success)',
            hover: 'var(--color-success)',
            light: 'var(--color-success)',
          },
          orange: {
            DEFAULT: 'var(--color-neutral)',
            hover: 'var(--color-neutral)',
            light: 'var(--color-neutral)',
          },
          blue: {
            DEFAULT: 'var(--color-white-60)',
            hover: 'var(--color-white)',
            light: 'var(--color-white-20)',
          }
        },
        // Status colors (for badges)
        status: {
          done: 'var(--color-success)',
          failed: 'var(--color-error)',
          pending: 'var(--color-neutral)',
          running: 'var(--color-neutral)',
        }
      },
    },
  },
  plugins: [],
}
