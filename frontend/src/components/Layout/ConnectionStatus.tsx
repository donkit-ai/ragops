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

  const getColor = () => {
    switch (status) {
      case 'connected':
        return 'text-status-done bg-status-done/10';
      case 'connecting':
        return 'text-status-running bg-status-running/10';
      case 'disconnected':
        return 'text-dark-text-secondary bg-dark-hover';
      case 'error':
        return 'text-status-failed bg-status-failed/10';
    }
  };

  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium ${getColor()}`}>
      {getIcon()}
      <span>{getText()}</span>
    </div>
  );
}
