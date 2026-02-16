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
    connected: { text: 'var(--color-success)' },
    connecting: { text: 'var(--color-neutral)' },
    disconnected: { text: 'var(--color-txt-icon-2)' },
    error: { text: 'var(--color-error)' }
  };
  const colors = colorMap[status];

  return (
    <div className="flex items-center font-medium" style={{ 
      gap: '6px', 
      fontSize: 'var(--font-size-p2)',
      color: colors.text
    }}>
      {getIcon()}
      <span>{getText()}</span>
    </div>
  );
}
