/**
 * Provider selection step in setup wizard
 */

import { ExternalLink, CheckCircle2 } from 'lucide-react';
import type { ProviderInfo } from '../../types/settings';

interface ProviderSelectionProps {
  providers: ProviderInfo[];
  onSelect: (provider: ProviderInfo) => void;
}

export default function ProviderSelection({ providers, onSelect }: ProviderSelectionProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-dark-text-secondary mb-4">
        Select your preferred LLM provider. You'll need an API key to get started.
      </p>

      {providers.map((provider) => (
        <button
          key={provider.name}
          onClick={() => onSelect(provider)}
          className="w-full p-4 rounded-lg border border-dark-border bg-dark-bg hover:border-accent-blue hover:bg-dark-bg/50 transition-all text-left group"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-dark-text-primary group-hover:text-accent-blue transition-colors">
                  {provider.display_name}
                </h3>
                {provider.is_configured && (
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-accent-green/10 rounded text-xs text-accent-green">
                    <CheckCircle2 className="w-3 h-3" />
                    Configured
                  </div>
                )}
              </div>
              <p className="text-sm text-dark-text-secondary mb-2">{provider.description}</p>
              {provider.documentation_url && (
                <a
                  href={provider.documentation_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-xs text-accent-blue hover:underline"
                >
                  Get API key
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
            <div className="text-2xl text-dark-text-muted group-hover:text-accent-blue transition-colors">
              →
            </div>
          </div>
        </button>
      ))}

      {providers.length === 0 && (
        <div className="text-center py-8">
          <p className="text-dark-text-muted">Loading providers...</p>
        </div>
      )}
    </div>
  );
}
