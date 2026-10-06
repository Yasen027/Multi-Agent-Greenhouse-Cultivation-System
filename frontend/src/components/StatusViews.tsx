/** 通用的加载 / 空数据展示组件 */

export function Loading({ label = '加载中…' }: { label?: string }) {
  return (
    <div className="status-view" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ icon = '🌱', title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="status-view empty">
      <span className="empty-icon" aria-hidden="true">
        {icon}
      </span>
      <p className="empty-title">{title}</p>
      {hint ? <p className="empty-hint">{hint}</p> : null}
    </div>
  );
}
