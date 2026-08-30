/** @type {import('tailwindcss').Config} */
// Design tokens are declared once in src/styles/tokens.css (docs/09-ui-design-system.md §2)
// and surfaced to Tailwind here, so components use semantic names
// (`bg-surface`, `text-primary`) instead of repeating raw hex or var() strings.
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        line: 'var(--color-border)',
        ink: {
          DEFAULT: 'var(--color-text-primary)',
          muted: 'var(--color-text-secondary)',
        },
        brand: {
          DEFAULT: 'var(--color-primary)',
          light: 'var(--color-primary-light)',
        },
        ok: 'var(--color-success)',
        warn: 'var(--color-warning)',
        bad: 'var(--color-danger)',
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'sans-serif',
        ],
      },
      maxWidth: {
        page: '1440px',
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)',
        lift: '0 4px 16px -2px rgb(15 23 42 / 0.08), 0 2px 6px -2px rgb(15 23 42 / 0.05)',
      },
      keyframes: {
        'rise-in': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'none' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        sweep: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'rise-in': 'rise-in 420ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'fade-in': 'fade-in 300ms ease-out both',
        sweep: 'sweep 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
