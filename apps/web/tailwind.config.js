/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        night: {
          950: 'var(--color-night-950)',
          900: 'var(--color-night-900)',
          800: 'var(--color-night-800)',
          700: 'var(--color-night-700)',
        },
        cyan: {
          DEFAULT: 'var(--color-cyan)',
          soft: 'var(--color-cyan-soft)',
        },
        electric: 'var(--color-electric)',
        amber: {
          DEFAULT: 'var(--color-amber)',
        },
        danger: 'var(--color-danger)',
      },
      fontFamily: {
        display: ['Rajdhani', 'Outfit', 'system-ui', 'sans-serif'],
        body: ['"Source Sans 3"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0, 0, 0, 0.45)',
        glow: '0 0 28px rgba(61, 227, 255, 0.35)',
      },
      animation: {
        'hud-spin': 'hud-spin 28s linear infinite',
      },
    },
  },
  plugins: [],
}
