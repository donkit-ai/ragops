import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react';
import { ConnectionStatus as Status } from '../../hooks/useWebSocket';

interface ConnectionStatusProps {
  status: Status;
}

export default function ConnectionStatus({ status }: ConnectionStatusProps) {
  const getIcon = () => {
    switch (status) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-status-done" />;
      case 'connecting':
        return <Loader2 className="w-4 h-4 text-status-running animate-spin" />;
      case 'disconnected':
        return <WifiOff className="w-4 h-4 text-dark-text-muted" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-status-failed" />;
    }
  };

  const getText = () => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection error';
    }
  };


  const colorMap = {
    connected: { text: 'var(--color-success)', bg: 'var(--color-action-item-selected)' },
    connecting: { text: 'var(--color-neutral)', bg: 'var(--color-action-item-selected)' },
    disconnected: { text: 'var(--color-txt-icon-2)', bg: 'var(--color-action-item-hover)' },
    error: { text: 'var(--color-error)', bg: 'var(--color-action-item-selected)' }
  };
  const colors = colorMap[status];

  return (
    <div className="flex items-center rounded-full font-medium" style={{ 
      gap: '6px', 
      padding: 'var(--space-xs) var(--space-s)', 
      fontSize: 'var(--font-size-p2)',
      color: colors.text,
      backgroundColor: colors.bg
    }}>
      {getIcon()}
      <span>{getText()}</span>
    </div>
  );
}
