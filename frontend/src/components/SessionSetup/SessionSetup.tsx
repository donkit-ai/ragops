import { ArrowRight, Building2, CheckCircle2, Cloud, Key, Loader2, Monitor, Plus, Settings } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSettings } from '../../hooks/useSettings';
import type { ProviderInfo } from '../../types/settings';
import SetupWizard from '../SetupWizard/SetupWizard';

interface SessionSetupProps {
  onStart: (options: { enterprise_mode: boolean; api_token?: string; provider?: string }) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}

export default function SessionSetup({ onStart, loading, error }: SessionSetupProps) {
  const [mode, setMode] = useState<'local' | 'saas' | 'enterprise'>('local');
  const [apiToken, setApiToken] = useState('');
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [showSetupWizard, setShowSetupWizard] = useState(false);
  const [configuredProviders, setConfiguredProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [checkingConfig, setCheckingConfig] = useState(false);
  const [donkitConfigured, setDonkitConfigured] = useState(false);

  const { getProviders } = useSettings();

  // Load configured providers (for both modes)
  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    setCheckingConfig(true);
    try {
      const response = await getProviders();

      // Check if donkit is configured (for both modes now)
      const donkitProvider = response.providers.find(p => p.name === 'donkit');
      setDonkitConfigured(donkitProvider?.is_configured ?? false);

      // Filter configured providers for local mode (donkit can be used in both modes now)
      const configured = response.providers.filter(p => p.is_configured);
      setConfiguredProviders(configured);

      // Auto-select first configured provider
      if (configured.length > 0 && !selectedProvider) {
        setSelectedProvider(configured[0].name);
      }
    } catch (err) {
      console.error('Failed to load providers:', err);
      setConfiguredProviders([]);
      setDonkitConfigured(false);
    } finally {
      setCheckingConfig(false);
    }
  };

  const handleStart = async () => {
    if (mode === 'saas') {
      // If donkit is configured and no manual token entered, use saved token
      if (donkitConfigured && !showTokenInput) {
        // Start directly with saved token
        await onStart({
          enterprise_mode: true,
          api_token: undefined,  // Backend will use saved token
          provider: undefined,
        });
        return;
      }

      // If not configured and token input not shown yet, show it
      if (!donkitConfigured && !showTokenInput) {
        setShowTokenInput(true);
        return;
      }
    }

    if (mode === 'local' && configuredProviders.length === 0) {
      // Show setup wizard for local mode without configured providers
      setShowSetupWizard(true);
      return;
    }

    await onStart({
      enterprise_mode: mode === 'saas',
      api_token: mode === 'saas' ? apiToken || undefined : undefined,
      provider: mode === 'local' ? selectedProvider || undefined : undefined,
    });
  };

  const handleModeChange = (newMode: 'local' | 'saas' | 'enterprise') => {
    setMode(newMode);
    setShowTokenInput(false);
    setApiToken('');
    setShowSetupWizard(false);
  };

  const handleSetupComplete = async () => {
    setShowSetupWizard(false);
    // Reload providers to show newly configured one
    await loadProviders();
  };

  const handleSetupBack = () => {
    setShowSetupWizard(false);
  };

  const handleAddProvider = () => {
    setShowSetupWizard(true);
  };

  // Show setup wizard if requested
  if (showSetupWizard) {
    return <SetupWizard onComplete={handleSetupComplete} onBack={handleSetupBack} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-bg to-dark-surface flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-dark-text-primary mb-2">RAGOps Agent</h1>
          <p className="text-dark-text-secondary">Choose your operating mode to get started</p>
        </div>

        {/* Mode Selection */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {/* Local Mode */}
          <button
            onClick={() => handleModeChange('local')}
            className={`
              p-6 rounded-xl border-2 transition-all h-full
              ${
                mode === 'local'
                  ? 'border-accent-blue bg-accent-blue/10 shadow-lg shadow-accent-blue/20'
                  : 'border-dark-border bg-dark-surface hover:border-dark-text-muted'
              }
            `}
          >
            <div className="flex flex-col items-center text-center h-full">
              <Monitor
                className={`w-12 h-12 mb-3 ${
                  mode === 'local' ? 'text-accent-blue' : 'text-dark-text-muted'
                }`}
              />
              <h3 className="font-semibold text-lg mb-1 text-dark-text-primary">Local</h3>
              <p className="text-sm text-dark-text-secondary">
                Run everything locally with your own LLM provider
              </p>
              <div className="flex-1" />
              <div className="pt-4 text-xs">
                {mode === 'local' && !checkingConfig ? (
                  configuredProviders.length > 0 ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-green/10 text-accent-green rounded">
                      <CheckCircle2 className="w-3 h-3" />
                      {configuredProviders.length} {configuredProviders.length === 1 ? 'provider' : 'providers'}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-orange/10 text-accent-orange rounded">
                      <Settings className="w-3 h-3" />
                      Setup required
                    </span>
                  )
                ) : (
                  <span className="invisible px-2 py-1">Placeholder</span>
                )}
              </div>
            </div>
          </button>

          {/* SaaS Mode */}
          <button
            onClick={() => handleModeChange('saas')}
            className={`
              p-6 rounded-xl border-2 transition-all h-full
              ${
                mode === 'saas'
                  ? 'border-accent-red bg-accent-red/10 shadow-lg shadow-accent-red/20'
                  : 'border-dark-border bg-dark-surface hover:border-dark-text-muted'
              }
            `}
          >
            <div className="flex flex-col items-center text-center h-full">
              <Cloud
                className={`w-12 h-12 mb-3 ${
                  mode === 'saas' ? 'text-accent-red' : 'text-dark-text-muted'
                }`}
              />
              <h3 className="font-semibold text-lg mb-1 text-dark-text-primary">SaaS</h3>
              <p className="text-sm text-dark-text-secondary">
                Connect to Donkit Cloud for managed RAG pipelines
              </p>
              <div className="flex-1" />
              <div className="pt-4 text-xs">
                {mode === 'saas' && !checkingConfig ? (
                  donkitConfigured ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-green/10 text-accent-green rounded">
                      <CheckCircle2 className="w-3 h-3" />
                      API Key configured
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-orange/10 text-accent-orange rounded">
                      <Key className="w-3 h-3" />
                      API Key required
                    </span>
                  )
                ) : (
                  <span className="invisible px-2 py-1">Placeholder</span>
                )}
              </div>
            </div>
          </button>

          {/* Enterprise Mode (On-Prem) */}
          <button
            disabled
            className="p-6 rounded-xl border-2 transition-all border-dark-border bg-dark-surface opacity-50 cursor-not-allowed h-full"
          >
            <div className="flex flex-col items-center text-center h-full">
              <Building2 className="w-12 h-12 mb-3 text-dark-text-muted" />
              <h3 className="font-semibold text-lg mb-1 text-dark-text-primary">Enterprise</h3>
              <p className="text-sm text-dark-text-secondary">
                Deploy locally on-premises or within your corporate VPC
              </p>
              <div className="flex-1" />
              <div className="pt-4 text-xs">
                <a
                  href="https://donkit.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2 py-1 bg-dark-bg text-dark-text-muted rounded hover:text-dark-text-primary transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  Contact Us
                </a>
              </div>
            </div>
          </button>
        </div>

        {/* Provider selection for Local Mode */}
        {mode === 'local' && configuredProviders.length > 0 && !checkingConfig && (
          <div className="mb-6 bg-dark-surface rounded-xl p-6 border border-dark-border shadow-sm">
            <h3 className="text-sm font-semibold text-dark-text-primary mb-3">Select Provider</h3>
            <div className="space-y-2">
              {configuredProviders.map((provider) => (
                <button
                  key={provider.name}
                  onClick={() => setSelectedProvider(provider.name)}
                  className={`
                    w-full p-3 rounded-lg border transition-all text-left
                    ${
                      selectedProvider === provider.name
                        ? 'border-accent-blue bg-accent-blue/10'
                        : 'border-dark-border bg-dark-bg hover:border-dark-text-muted'
                    }
                  `}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-dark-text-primary">{provider.display_name}</div>
                      <div className="text-xs text-dark-text-muted">{provider.description}</div>
                    </div>
                    {selectedProvider === provider.name && (
                      <CheckCircle2 className="w-5 h-5 text-accent-blue flex-shrink-0" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Configuration hint for Local Mode */}
        {mode === 'local' && configuredProviders.length === 0 && !checkingConfig && (
          <div className="mb-6 p-4 bg-accent-blue/10 border border-accent-blue/30 rounded-lg">
            <p className="text-sm text-dark-text-primary">
              <strong>First time setup:</strong> You'll need to configure at least one LLM provider (OpenAI, Vertex AI, etc.) before starting.
              Click "Setup Provider" below to get started.
            </p>
          </div>
        )}

        {/* API Token Input (SaaS only) */}
        {mode === 'saas' && showTokenInput && (
          <div className="mb-6 bg-dark-surface rounded-xl p-6 border border-dark-border shadow-sm">
            <label className="block mb-2">
              <div className="flex items-center gap-2 text-sm font-medium text-dark-text-primary mb-2">
                <Key className="w-4 h-4" />
                API Token (optional)
              </div>
              <input
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="Enter your API token or leave empty to use saved token"
                className="w-full px-4 py-2.5 bg-dark-bg border border-dark-border rounded-lg text-dark-text-primary placeholder:text-dark-text-muted focus:ring-2 focus:ring-accent-red focus:border-transparent"
              />
            </label>
            <p className="text-xs text-dark-text-muted mt-2">
              If you've already logged in via CLI (<code className="bg-dark-bg px-2 py-0.5 rounded">donkit-ragops login</code>), you can
              leave this empty.
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-accent-red/10 border border-accent-red/30 rounded-lg">
            <p className="text-accent-red text-sm">{error}</p>
          </div>
        )}

        {/* Start Button */}
        <button
          onClick={handleStart}
          disabled={loading || checkingConfig}
          className={`
            w-full py-4 rounded-xl font-semibold text-white
            flex items-center justify-center gap-2
            transition-all
            ${
              mode === 'local'
                ? 'bg-accent-blue hover:bg-accent-blue-hover'
                : mode === 'saas'
                  ? 'bg-accent-red hover:bg-accent-red-hover'
                  : 'bg-dark-text-muted'
            }
            ${loading || checkingConfig ? 'opacity-50 cursor-not-allowed' : 'shadow-lg hover:shadow-xl'}
          `}
        >
          {loading || checkingConfig ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {checkingConfig ? 'Checking configuration...' : 'Starting...'}
            </>
          ) : (
            <>
              {mode === 'saas' && !donkitConfigured && !showTokenInput ? (
                <>
                  Next
                  <ArrowRight className="w-5 h-5" />
                </>
              ) : mode === 'local' && configuredProviders.length === 0 ? (
                <>
                  <Settings className="w-5 h-5" />
                  Setup Provider
                </>
              ) : (
                <>
                  Start {mode === 'local' ? 'Local' : 'SaaS'} Mode
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </>
          )}
        </button>

        {/* Add/Manage providers button for local mode */}
        {mode === 'local' && (
          <button
            onClick={handleAddProvider}
            disabled={loading || checkingConfig}
            className="w-full mt-3 py-2 text-sm text-dark-text-muted hover:text-dark-text-primary flex items-center justify-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {configuredProviders.length === 0 ? 'Add Provider' : 'Add/Manage Providers'}
          </button>
        )}

        {/* Use different token button for SaaS mode */}
        {mode === 'saas' && donkitConfigured && !showTokenInput && (
          <button
            onClick={() => setShowTokenInput(true)}
            disabled={loading || checkingConfig}
            className="w-full mt-3 py-2 text-sm text-dark-text-muted hover:text-dark-text-primary flex items-center justify-center gap-2 transition-colors"
          >
            <Key className="w-4 h-4" />
            Use a different API key
          </button>
        )}

        {/* Info Footer */}
        <div className="mt-8 text-center text-sm text-dark-text-muted">
          <p>Need help? Run <code className="bg-dark-surface border border-dark-border px-2 py-1 rounded">donkit-ragops --help</code></p>
        </div>
      </div>
    </div>
  );
}
