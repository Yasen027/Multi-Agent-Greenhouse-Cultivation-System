/** 前端入口：挂载 React 应用到 #root */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './style.css';

// 定位 index.html 中的 #root 挂载节点；不存在则直接抛错中断启动
const container = document.getElementById('root');
if (!container) {
  throw new Error('找不到 #root 挂载节点，请检查 index.html');
}

// React 18 createRoot 入口；StrictMode 在开发模式下会双重调用以暴露副作用问题
createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
