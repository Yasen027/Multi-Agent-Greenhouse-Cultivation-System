/** 顶部告警横幅：展示后端不可用等错误、警告与提示，支持手动重试 */

export type AlertKind = 'error' | 'warning' | 'info' | 'success';

const KIND_ICON: Record<AlertKind, string> = {
  error: '⛔',
  warning: '⚠️',
  info: 'ℹ️',
  success: '✅',
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
  return (
    <div className={`alert alert-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <span className="alert-icon" aria-hidden="true">
        {KIND_ICON[kind]}
      </span>
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
