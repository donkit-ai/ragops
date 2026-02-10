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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-m)' }}>
      <p className="p2" style={{ marginBottom: 'var(--space-m)', color: 'var(--color-txt-icon-2)' }}>
        Select your preferred LLM provider. You'll need an API key to get started.
      </p>

      {providers.map((provider) => (
        <button
          key={provider.name}
          onClick={() => onSelect(provider)}
          className="w-full text-left transition-all group"
          style={{
            padding: 'var(--space-m)',
            borderRadius: 'var(--space-s)',
            border: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-bg)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--color-white-60)';
            e.currentTarget.style.backgroundColor = 'rgba(14, 15, 17, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--color-border)';
            e.currentTarget.style.backgroundColor = 'var(--color-bg)';
          }}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center" style={{ gap: 'var(--space-s)', marginBottom: 'var(--space-xs)' }}>
                <h3 className="h4 group-hover:transition-colors" style={{ fontWeight: 500 }}>{provider.display_name}</h3>
                {provider.is_configured && (
                  <div className="flex items-center" style={{ gap: 'var(--space-xs)', padding: '2px var(--space-s)', backgroundColor: 'rgba(0, 200, 110, 0.1)', borderRadius: 'var(--space-xs)', fontSize: 'var(--font-size-p2)', color: 'var(--color-success)' }}>
                    <CheckCircle2 className="w-3 h-3" />
                    Configured
                  </div>
                )}
              </div>
              <p className="p2" style={{ marginBottom: 'var(--space-s)', color: 'var(--color-txt-icon-2)' }}>{provider.description}</p>
              {provider.documentation_url && (
                <a
                  href={provider.documentation_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center"
                  style={{ gap: 'var(--space-xs)', fontSize: 'var(--font-size-p2)', color: 'var(--color-white-60)' }}
                  onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                  onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                >
                  Get API key
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
            <div style={{ fontSize: '24px', color: 'var(--color-txt-icon-2)' }} className="group-hover:transition-colors">
              →
            </div>
          </div>
        </button>
      ))}

      {providers.length === 0 && (
        <div className="text-center" style={{ padding: 'var(--space-xl) 0' }}>
          <p style={{ color: 'var(--color-txt-icon-2)' }}>Loading providers...</p>
        </div>
      )}
    </div>
  );
}
