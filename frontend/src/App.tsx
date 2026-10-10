/** 应用外壳：Shadcn Dashboard 风格侧栏、页头、后端健康状态与页面切换。 */

import { useEffect, useState, type ComponentType } from 'react';
import {
  Bot,
  ClipboardCheck,
  History,
  LayoutDashboard,
  Leaf,
  Map,
  Radio,
  ServerOff,
} from 'lucide-react';
import { usePolling } from './hooks/usePolling';
import { Agents } from './pages/Agents';
import { Dashboard } from './pages/Dashboard';
import { GreenhouseMap } from './pages/GreenhouseMap';
import { History as HistoryPage } from './pages/History';
import { HITL } from './pages/HITL';
import { api } from './services/api';

/** 路由 id 联合类型；Icon 为 lucide 图标的通用组件类型 */
type RouteId = 'dashboard' | 'agents' | 'hitl' | 'history' | 'map';
type Icon = ComponentType<{ size?: number; strokeWidth?: number; 'aria-hidden'?: boolean }>;

// 侧栏导航配置：id 对应 hash 路由，description 同时用作页头标题
const NAV: { id: RouteId; label: string; description: string; icon: Icon }[] = [
  { id: 'dashboard', label: '种植总栏', description: '实时态势与决策', icon: LayoutDashboard },
  { id: 'agents', label: '智能体集群', description: '专家状态与置信度', icon: Bot },
  { id: 'hitl', label: '人工审批', description: '安全拦截与复核', icon: ClipboardCheck },
  { id: 'history', label: '历史审计', description: '全链路事件追溯', icon: History },
  { id: 'map', label: '温室地图', description: '分区与设备点位', icon: Map },
];

/** 把 location.hash（如 "#/agents?x=1"）规范化为合法路由 id，未知值回退到 dashboard */
function normalizeRoute(hash: string): RouteId {
  const id = hash.replace(/^#\/?/, '').split('?')[0].toLowerCase();
  return NAV.some((n) => n.id === id) ? (id as RouteId) : 'dashboard';
}

/** 基于 hash 的路由 Hook：监听 hashchange 事件，实现无刷新页面切换 */
function useHashRoute(): RouteId {
  const [route, setRoute] = useState<RouteId>(() => normalizeRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(normalizeRoute(window.location.hash));
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

/** 页头后端健康状态胶囊：4 秒轮询 /api/health，在线时显示后端版本号 */
function HealthStatus() {
  const { data, error, lastUpdated } = usePolling(api.getHealth);
  const online = !error && data?.status === 'ok';
  const StatusIcon = online ? Radio : ServerOff;

  return (
    <div className={`health ${online ? 'health-ok' : 'health-down'}`} title={error ? error.message : '后端服务在线'}>
      <StatusIcon size={15} aria-hidden />
      <span className="health-dot" aria-hidden="true" />
      <span className="health-text">
        {online ? '系统在线' : '连接中断'}
        {lastUpdated && online ? ` · v${data?.version ?? '?'}` : ''}
      </span>
    </div>
  );
}

/** 应用外壳：侧栏品牌与导航、顶栏、当前路由页面与页脚 */
export default function App() {
  const route = useHashRoute();
  const current = NAV.find((item) => item.id === route) ?? NAV[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#/dashboard" aria-label="返回种植总栏">
          <span className="brand-mark" aria-hidden="true">
            <Leaf size={23} strokeWidth={2.4} />
          </span>
          <span>
            <strong className="brand-title">Greenhouse OS</strong>
            <span className="brand-sub">多智能体温室种植系统</span>
          </span>
        </a>

        <div className="nav-caption">智能控制中心</div>
        <nav className="app-nav" aria-label="主导航">
          {NAV.map((item) => {
            const NavIcon = item.icon;
            return (
              <a
                key={item.id}
                href={`#/${item.id}`}
                className={`nav-link ${route === item.id ? 'nav-active' : ''}`}
                aria-current={route === item.id ? 'page' : undefined}
              >
                <NavIcon size={19} strokeWidth={1.9} aria-hidden />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="app-content">
        <header className="topbar">
          <div>
            <p className="topbar-kicker">温室数字孪生 / {current.label}</p>
            <h1 className="topbar-title">{current.description}</h1>
          </div>
          <HealthStatus />
        </header>

        <main className="app-main">
          {/* 按当前路由渲染对应页面（条件互斥，同一时刻仅一个页面挂载） */}
          {route === 'dashboard' ? <Dashboard /> : null}
          {route === 'agents' ? <Agents /> : null}
          {route === 'hitl' ? <HITL /> : null}
          {route === 'history' ? <HistoryPage /> : null}
          {route === 'map' ? <GreenhouseMap /> : null}
        </main>

        <footer className="app-footer">
          数据每 4 秒自动刷新 · 页面不可见时暂停轮询 · 全流程保留审计记录
        </footer>
      </div>
    </div>
  );
}
