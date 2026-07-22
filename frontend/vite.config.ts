import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/documents': {
        target: 'http://localhost:8000',
        ws: true,
      },
      '/folders': 'http://localhost:8000',
      '/clusters': 'http://localhost:8000',
      '/search': 'http://localhost:8000',
      '/rules': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
