/** 通用的加载 / 空数据展示组件 */

import { Sprout } from 'lucide-react';
import type { ReactNode } from 'react';

/** 加载中占位：旋转动画 + 文案；role=status 供读屏播报 */
export function Loading({ label = '加载中…' }: { label?: string }) {
  return (
    <div className="status-view" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

/** 空数据占位：图标 + 标题 + 可选提示语 */
export function EmptyState({ icon = <Sprout size={36} />, title, hint }: { icon?: ReactNode; title: string; hint?: string }) {
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
