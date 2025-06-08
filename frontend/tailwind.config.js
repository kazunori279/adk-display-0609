/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Inter', 'Noto Sans', 'sans-serif'],
      },
      colors: {
        'primary': '#0b79ee',
        'text-primary': '#111418',
        'text-secondary': '#60758a',
        'bg-secondary': '#f0f2f5',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ],
}