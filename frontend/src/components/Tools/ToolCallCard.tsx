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

  const statusColorMap = {
    running: { border: 'var(--color-border)', bg: 'var(--color-action-item-selected)' },
    completed: { border: 'var(--color-border)', bg: 'var(--color-action-item-selected)' },
    error: { border: 'var(--color-border)', bg: 'var(--color-action-item-selected)' }
  };
  const colors = statusColorMap[toolCall.status];

  return (
    <div style={{ 
      border: `1px solid ${colors.border}`, 
      borderRadius: 'var(--space-s)', 
      padding: '10px',
      backgroundColor: colors.bg
    }}>
      <div className="flex items-center" style={{ gap: 'var(--space-s)' }}>
        <Wrench className="w-4 h-4" style={{ color: 'var(--color-txt-icon-2)' }} />
        <span className="font-mono p2" style={{ fontWeight: 500 }}>{toolCall.name}</span>
        {getStatusIcon()}
      </div>

      {/* Arguments */}
      {Object.keys(toolCall.args).length > 0 && (
        <div className="p2" style={{ marginTop: '6px', color: 'var(--color-txt-icon-2)' }}>
          <details>
            <summary style={{ cursor: 'pointer' }} onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-txt-icon-1)'} onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-txt-icon-2)'}>Arguments</summary>
            <pre style={{ 
              marginTop: 'var(--space-xs)', 
              backgroundColor: 'var(--color-action-item-selected)', 
              border: '1px solid var(--color-border)', 
              borderRadius: 'var(--space-xs)', 
              padding: '6px', 
              overflowX: 'auto',
              fontSize: 'var(--font-size-p2)'
            }}>
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {/* Result preview */}
      {toolCall.resultPreview && (
        <div className="p2" style={{ marginTop: '6px', color: 'var(--color-txt-icon-2)' }}>
          <details>
            <summary style={{ cursor: 'pointer' }} onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-txt-icon-1)'} onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-txt-icon-2)'}>Result</summary>
            <pre style={{ 
              marginTop: 'var(--space-xs)', 
              backgroundColor: 'rgba(14, 15, 17, 0.5)', 
              border: '1px solid var(--color-border)', 
              borderRadius: 'var(--space-xs)', 
              padding: '6px', 
              overflowX: 'auto',
              maxHeight: '128px',
              fontSize: 'var(--font-size-p2)'
            }}>
              {toolCall.resultPreview}
            </pre>
          </details>
        </div>
      )}

      {/* Error */}
      {toolCall.error && (
        <div className="p2" style={{ marginTop: '6px', color: 'var(--color-error)' }}>
          Error: {toolCall.error}
        </div>
      )}
    </div>
  );
}
