import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/login': 'http://localhost:5000',
      '/register': 'http://localhost:5000',
      '/me': 'http://localhost:5000',
      '/api': 'http://localhost:5000',
      '/auth': 'http://localhost:5000',
      '/update_profile': 'http://localhost:5000'
    }
  }
})
