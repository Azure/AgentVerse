/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta whitelabel: azul corporativo neutro como primario.
        // Editar estos valores para cambiar el color principal de marca.
        primary: {
          50:  '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#2563EB', // Brand main (blue-600)
          600: '#1D4ED8',
          700: '#1E40AF',
          800: '#1E3A8A',
          900: '#172554',
        },
        // Alias semánticos para acceso rápido
        brand: {
          blue:       '#2563EB',
          'blue-700': '#1E40AF',
          'blue-50':  '#EFF6FF',
          dark:      '#0F172A',
          gray:      '#475569',
          'gray-light': '#F1F5F9',
        },
        accent: { 400: '#FFD24C', 500: '#FFC107', 600: '#E0A800' },
        // Light surfaces para hero, cards, header
        surface: {
          0:   '#FFFFFF',
          50:  '#F8FAFC',
          100: '#F1F5F9',
          150: '#E5E7EB',
          200: '#CBD5E1',
          // mantenemos tonos oscuros para zonas tipo "panel de control"
          800: '#1F2937',
          850: '#111827',
          900: '#0F172A',
          950: '#020617',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
