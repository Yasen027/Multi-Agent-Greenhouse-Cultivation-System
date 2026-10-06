import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 开发服务器配置：
// - /api  → http://localhost:8000（REST 接口）
// - /ws   → ws://localhost:8000（WebSocket，后续阶段由轮询切换为推送）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  preview: {
    port: 4173,
  },
});
