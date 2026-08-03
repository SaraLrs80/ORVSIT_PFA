import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // react()       -> permet d'écrire des composants React (.jsx)
  // tailwindcss() -> active Tailwind CSS pendant le développement et le build
  plugins: [react(), tailwindcss()],
})
