import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

// 前端固定 8080，后端固定 5000；/api 与 /static 都代理到后端，
// 避免开发态跨域与图片 404（PRD 9.3）。
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8080,
    host: '127.0.0.1',
    proxy: {
      '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:5000', changeOrigin: true }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia']
        }
      }
    }
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  }
})
