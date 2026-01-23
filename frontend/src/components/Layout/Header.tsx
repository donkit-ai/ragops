import { Database } from 'lucide-react';

interface HeaderProps {
  provider?: string;
  model?: string | null;
}

export default function Header({ provider, model }: HeaderProps) {
  return (
    <header className="bg-dark-surface border-b border-dark-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent-red rounded-lg flex items-center justify-center">
            <Database className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-dark-text-primary">RAGOps</h1>
            <p className="text-sm text-dark-text-secondary">AI-Powered RAG Pipeline Builder</p>
          </div>
        </div>
        {provider && (
          <div className="text-sm text-dark-text-secondary">
            <span className="font-medium">{provider}</span>
            {model && <span className="text-dark-text-muted ml-1">/ {model}</span>}
          </div>
        )}
      </div>
    </header>
  );
}
