/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        base: '#080C14',
        panel: '#0F1623',
        elevated: '#162033',
        border: '#1E2D45',
        'border-main': '#1E2D45',
        primary: '#E8EDF5',
        secondary: '#7A8FA8',
        fire: '#FF4444',
        flare: '#FF8C00',
        agri: '#F5C518',
        wild: '#3DB86B',
        unknown: '#4A5568',
        blue: '#2D7DD2',
        // Token names mapping directly to prompt specs:
        'bg-base': '#080C14',
        'bg-panel': '#0F1623',
        'bg-elevated': '#162033',
        'text-primary': '#E8EDF5',
        'text-secondary': '#7A8FA8',
        'accent-fire': '#FF4444',
        'accent-flare': '#FF8C00',
        'accent-agri': '#F5C518',
        'accent-wild': '#3DB86B',
        'accent-unknown': '#4A5568',
        'accent-blue': '#2D7DD2',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
};
