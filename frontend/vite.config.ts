/** Vite 构建配置：React 插件、开发代理与构建输出设置。 */
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
  // 生产构建：输出到 dist 并先清空目录，不生成 sourcemap 以减小体积
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  // vite preview 本地预览端口
  preview: {
    port: 4173,
  },
});
