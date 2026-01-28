import { Loader2, CheckCircle2, XCircle, Wrench } from 'lucide-react';
import { ToolCall } from '../../types/protocol';

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin text-status-running" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-status-done" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-status-failed" />;
    }
  };

  const getStatusColor = () => {
    switch (toolCall.status) {
      case 'running':
        return 'border-status-running/30 bg-status-running/5';
      case 'completed':
        return 'border-status-done/30 bg-status-done/5';
      case 'error':
        return 'border-status-failed/30 bg-status-failed/5';
    }
  };

  return (
    <div className={`border rounded-lg p-2.5 ${getStatusColor()}`}>
      <div className="flex items-center gap-2">
        <Wrench className="w-4 h-4 text-dark-text-muted" />
        <span className="font-mono text-sm font-medium text-dark-text-primary">{toolCall.name}</span>
        {getStatusIcon()}
      </div>

      {/* Arguments */}
      {Object.keys(toolCall.args).length > 0 && (
        <div className="mt-1.5 text-xs text-dark-text-secondary">
          <details>
            <summary className="cursor-pointer hover:text-dark-text-primary">Arguments</summary>
            <pre className="mt-1 bg-dark-bg/50 border border-dark-border rounded p-1.5 overflow-x-auto">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Result preview */}
      {toolCall.resultPreview && (
        <div className="mt-1.5 text-xs text-dark-text-secondary">
          <details>
            <summary className="cursor-pointer hover:text-dark-text-primary">Result</summary>
            <pre className="mt-1 bg-dark-bg/50 border border-dark-border rounded p-1.5 overflow-x-auto max-h-32">
              {toolCall.resultPreview}
            </pre>
          </details>
        </div>
      )}

      {/* Error */}
      {toolCall.error && (
        <div className="mt-1.5 text-xs text-status-failed">
          Error: {toolCall.error}
        </div>
      )}
    </div>
  );
}
