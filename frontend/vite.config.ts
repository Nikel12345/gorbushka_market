import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      // В dev-режиме запросы к /api проксируются на Django,
      // поэтому фронт и бэк работают как один origin (без CORS и с cookie).
      proxy: {
        '/api': {
          target: env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        // Загруженные файлы (фото товаров): API отдаёт относительные URL /media/...
        '/media': {
          target: env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
