import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Portal 服务
      '/auth': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
      '/api/subsystems': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
      // NL2SQL 服务
      '/api/nl2sql': {
        target: 'http://localhost:8011',
        changeOrigin: true,
      },
      // 敏感数据检测服务
      '/api/sensitive': {
        target: 'http://localhost:8015',
        changeOrigin: true,
      },
      // 审计日志服务
      '/api/audit': {
        target: 'http://localhost:8016',
        changeOrigin: true,
      },
    },
  },
})
