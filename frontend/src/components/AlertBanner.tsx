/** 顶部告警横幅：展示后端不可用等错误、警告与提示，支持手动重试 */

import { AlertTriangle, CheckCircle2, CircleAlert, Info, type LucideIcon } from 'lucide-react';

export type AlertKind = 'error' | 'warning' | 'info' | 'success';

// 告警类型 → 图标（error 实心警示、warning 三角、info 信息、success 对勾）
const KIND_ICON: Record<AlertKind, LucideIcon> = {
  error: CircleAlert,
  warning: AlertTriangle,
  info: Info,
  success: CheckCircle2,
};

interface AlertBannerProps {
  kind: AlertKind;
  title?: string;
  message: string;
  onRetry?: () => void;
  /** 是否显示小型行内加载态（如重试中） */
  retrying?: boolean;
}

export function AlertBanner({ kind, title, message, onRetry, retrying = false }: AlertBannerProps) {
  const KindIcon = KIND_ICON[kind];
  // title 缺省时按类型生成默认标题；传入 onRetry 时才显示重试按钮
  return (
    <div className={`alert alert-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <span className="alert-icon" aria-hidden="true"><KindIcon size={19} /></span>
      <div className="alert-body">
        <p className="alert-title">{title ?? (kind === 'error' ? '后端服务异常' : kind === 'warning' ? '警告' : '提示')}</p>
        <p className="alert-message">{message}</p>
      </div>
      {onRetry ? (
        <button type="button" className="btn btn-small" onClick={onRetry} disabled={retrying}>
          {retrying ? '重试中…' : '重试'}
        </button>
      ) : null}
    </div>
  );
}
