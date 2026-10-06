/** 前端入口：挂载 React 应用到 #root */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './style.css';

const container = document.getElementById('root');
if (!container) {
  throw new Error('找不到 #root 挂载节点，请检查 index.html');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
