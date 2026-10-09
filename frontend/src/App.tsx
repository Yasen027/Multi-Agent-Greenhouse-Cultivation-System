/** 应用外壳：顶部导航（hash 路由）+ 后端健康状态 + 页面切换 */

import { useEffect, useState } from 'react';
import { usePolling } from './hooks/usePolling';
import { Agents } from './pages/Agents';
import { Dashboard } from './pages/Dashboard';
import { GreenhouseMap } from './pages/GreenhouseMap';
import { History } from './pages/History';
import { HITL } from './pages/HITL';
import { api } from './services/api';

type RouteId = 'dashboard' | 'agents' | 'hitl' | 'history' | 'map';

const NAV: { id: RouteId; label: string; icon: string }[] = [
  { id: 'dashboard', label: '总览', icon: '📊' },
  { id: 'agents', label: '智能体', icon: '🤖' },
  { id: 'hitl', label: '人工审批', icon: '🧑‍🌾' },
  { id: 'history', label: '历史审计', icon: '🗂️' },
  { id: 'map', label: '温室地图', icon: '🗺️' },
];

function normalizeRoute(hash: string): RouteId {
  const id = hash.replace(/^#\/?/, '').split('?')[0].toLowerCase();
  return NAV.some((n) => n.id === id) ? (id as RouteId) : 'dashboard';
}

function useHashRoute(): RouteId {
  const [route, setRoute] = useState<RouteId>(() => normalizeRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(normalizeRoute(window.location.hash));
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

function HealthDot() {
  const { data, error, lastUpdated } = usePolling(api.getHealth);
  const online = !error && data?.status === 'ok';
  return (
    <div className={`health ${online ? 'health-ok' : 'health-down'}`} title={error ? error.message : '后端服务在线'}>
      <span className="health-dot" aria-hidden="true" />
      <span className="health-text">
        {online ? '后端在线' : '后端不可用'}
        {lastUpdated && online ? ` · v${data?.version ?? '?'}` : ''}
      </span>
    </div>
  );
}

export default function App() {
  const route = useHashRoute();

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            🌱
          </span>
          <div>
            <h1 className="brand-title">温室多智能体控制台</h1>
          </div>
        </div>
        <HealthDot />
      </header>

      <nav className="app-nav" aria-label="主导航">
        {NAV.map((item) => (
          <a
            key={item.id}
            href={`#/${item.id}`}
            className={`nav-link ${route === item.id ? 'nav-active' : ''}`}
            aria-current={route === item.id ? 'page' : undefined}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.label}
          </a>
        ))}
      </nav>

      <main className="app-main">
        {route === 'dashboard' ? <Dashboard /> : null}
        {route === 'agents' ? <Agents /> : null}
        {route === 'hitl' ? <HITL /> : null}
        {route === 'history' ? <History /> : null}
        {route === 'map' ? <GreenhouseMap /> : null}
      </main>

      <footer className="app-footer">
        <p>
          数据每 4 秒自动刷新（3–5 秒轮询） · 页面不可见时暂停刷新 · 后续阶段将切换为 /ws/updates WebSocket 推送
        </p>
      </footer>
    </div>
  );
}
