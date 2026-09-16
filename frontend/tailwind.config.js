/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0d1117',
          card: '#161b22',
          cardHover: '#1f242c',
          border: '#30363d',
          input: '#21262d',
          muted: '#8b949e',
          text: '#c9d1d9',
          heading: '#f0f6fc',
        },
        gh: {
          green: '#238636',
          greenHover: '#2ea043',
          greenBright: '#3fb950',
          yellow: '#d29922',
          red: '#f85149',
          blue: '#58a6ff',
          purple: '#bc8cff',
          darkBorder: '#30363d'
        }
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(35, 134, 54, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(63, 185, 80, 0.6)' },
        }
      }
    },
  },
  plugins: [],
}
