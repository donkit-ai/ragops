import { useState } from 'react';
import { Check, X } from 'lucide-react';

interface ConfirmDialogProps {
  requestId: string;
  question: string;
  defaultValue: boolean;
  onResponse: (requestId: string, confirmed: boolean) => void;
}

export function ConfirmDialog({
  requestId,
  question,
  defaultValue,
  onResponse,
}: ConfirmDialogProps) {
  const [responded, setResponded] = useState(false);

  const handleResponse = (confirmed: boolean) => {
    console.log('[ConfirmDialog] handleResponse called:', { requestId, confirmed, responded });
    if (responded) return;
    setResponded(true);
    onResponse(requestId, confirmed);
  };

  return (
    <div style={{ 
      backgroundColor: 'var(--color-action-item-selected)', 
      border: '1px solid var(--color-border)', 
      borderRadius: 'var(--space-s)', 
      padding: 'var(--space-m)', 
      margin: 'var(--space-s) 0' 
    }}>
      <p className="p1" style={{ marginBottom: 'var(--space-m)', whiteSpace: 'pre-wrap' }}>{question}</p>
      {!responded ? (
        <div className="flex" style={{ gap: 'var(--space-s)' }}>
          <button
            onClick={() => handleResponse(true)}
            className="btn-primary flex items-center font-medium transition-colors"
            style={{
              gap: '6px',
            }}
            onMouseEnter={(e) => {
              if (!responded) {
                e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)';
              }
            }}
            onMouseLeave={(e) => {
              if (!responded) {
                e.currentTarget.style.backgroundColor = 'var(--color-accent)';
              }
            }}
          >
            <Check className="w-4 h-4" />
            Yes
          </button>
          <button
            onClick={() => handleResponse(false)}
            className="btn-secondary flex items-center font-medium transition-colors"
            style={{
              gap: '6px',
            }}
          >
            <X className="w-4 h-4" />
            No
          </button>
        </div>
      ) : (
        <p className="p2" style={{ color: 'var(--color-txt-icon-2)', fontStyle: 'italic' }}>Response submitted</p>
      )}
    </div>
  );
}

interface ChoiceDialogProps {
  requestId: string;
  title: string;
  choices: string[];
  onResponse: (requestId: string, choice: string) => void;
}

export function ChoiceDialog({
  requestId,
  title,
  choices,
  onResponse,
}: ChoiceDialogProps) {
  const [responded, setResponded] = useState(false);
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);

  const handleResponse = (choice: string) => {
    if (responded) return;
    setResponded(true);
    setSelectedChoice(choice);
    onResponse(requestId, choice);
  };

  return (
    <div style={{ 
      backgroundColor: 'var(--color-action-item-selected)', 
      border: '1px solid var(--color-border)', 
      borderRadius: 'var(--space-s)', 
      padding: 'var(--space-m)', 
      margin: 'var(--space-s) 0' 
    }}>
      <p className="p1" style={{ fontWeight: 500, marginBottom: 'var(--space-m)' }}>{title}</p>
      {!responded ? (
        <div className="flex flex-wrap" style={{ gap: 'var(--space-s)' }}>
          {choices.map((choice, index) => (
            <button
              key={index}
              onClick={() => handleResponse(choice)}
              className="transition-colors"
              style={{
                padding: 'var(--space-s) var(--space-m)',
                backgroundColor: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--space-s)',
                color: 'var(--color-txt-icon-1)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-action-item-hover)';
                e.currentTarget.style.borderColor = 'var(--color-accent)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg)';
                e.currentTarget.style.borderColor = 'var(--color-border)';
              }}
            >
              {choice}
            </button>
          ))}
        </div>
      ) : (
        <p className="p2" style={{ color: 'var(--color-txt-icon-2)', fontStyle: 'italic' }}>
          Selected: <span style={{ fontWeight: 500, color: 'var(--color-txt-icon-1)' }}>{selectedChoice}</span>
        </p>
      )}
    </div>
  );
}
