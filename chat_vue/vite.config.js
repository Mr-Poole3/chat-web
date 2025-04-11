import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    port: 7863,
    host: true,
    proxy: {
      '/api/v1': {
        target: 'http://0.0.0.0:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://0.0.0.0:8000',
        ws: true,
      }
    },
    hmr: {
      // 禁用 WebSocket 压缩，可能导致某些环境下的兼容性问题
      // 这可以解决 'Invalid WebSocket frame: RSV1 must be clear' 错误
      clientPort: 24678,
      protocol: 'ws'
    }
  }
})
