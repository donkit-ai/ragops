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
    <div className="bg-accent-blue/10 border border-accent-blue/30 rounded-lg p-4 my-2">
      <p className="text-dark-text-primary mb-3 whitespace-pre-wrap">{question}</p>
      {!responded ? (
        <div className="flex gap-2">
          <button
            onClick={() => handleResponse(true)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium transition-colors ${
              defaultValue
                ? 'bg-accent-green text-white hover:bg-accent-green-hover'
                : 'bg-dark-hover text-dark-text-secondary hover:bg-dark-border'
            }`}
          >
            <Check className="w-4 h-4" />
            Yes
          </button>
          <button
            onClick={() => handleResponse(false)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium transition-colors ${
              !defaultValue
                ? 'bg-accent-red text-white hover:bg-accent-red-hover'
                : 'bg-dark-hover text-dark-text-secondary hover:bg-dark-border'
            }`}
          >
            <X className="w-4 h-4" />
            No
          </button>
        </div>
      ) : (
        <p className="text-dark-text-muted text-sm italic">Response submitted</p>
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
    <div className="bg-accent-red/10 border border-accent-red/30 rounded-lg p-4 my-2">
      <p className="text-dark-text-primary font-medium mb-3">{title}</p>
      {!responded ? (
        <div className="flex flex-wrap gap-2">
          {choices.map((choice, index) => (
            <button
              key={index}
              onClick={() => handleResponse(choice)}
              className="px-4 py-2 bg-dark-bg border border-dark-border rounded-lg
                         text-dark-text-primary hover:bg-dark-hover hover:border-accent-red
                         transition-colors"
            >
              {choice}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-dark-text-muted text-sm italic">
          Selected: <span className="font-medium text-dark-text-primary">{selectedChoice}</span>
        </p>
      )}
    </div>
  );
}
