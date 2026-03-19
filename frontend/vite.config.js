import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@douyinfe/semi-ui/dist/css/semi.min.css': path.resolve(
        __dirname,
        'node_modules/@douyinfe/semi-ui/dist/css/semi.min.css'
      ),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        // 透传客户端来源信息，便于后端日志记录真实 IP
        xfwd: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
