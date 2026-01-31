import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/auth': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../services/portal/static',
    emptyOutDir: true,
  },
})
