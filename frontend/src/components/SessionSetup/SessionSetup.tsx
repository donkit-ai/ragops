import { ArrowRight, CheckCircle2, Copy, Key, Loader2, Plus, Settings } from 'lucide-react';
import DonkitIcon from '../../assets/donkit-icon-round.svg';
import LocalModeIcon from '../../assets/icons/laptop-minimal-check.svg';
import SaaSModeIcon from '../../assets/icons/cloud.svg';
import EnterpriseModeIcon from '../../assets/icons/building-2.svg';
import AlertIcon from '../../assets/icons/triangle-alert.svg';
import ThemeSystemIcon from '../../assets/icons/monitor-cog.svg';
import ThemeLightIcon from '../../assets/icons/sun.svg';
import ThemeDarkIcon from '../../assets/icons/moon-star.svg';
import { useEffect, useState } from 'react';
import { useSettings } from '../../hooks/useSettings';
import type { ProviderInfo } from '../../types/settings';
import SetupWizard from '../SetupWizard/SetupWizard';

interface SessionSetupProps {
  onStart: (options: { enterprise_mode: boolean; api_token?: string; provider?: string }) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}

type Mode = 'local' | 'saas' | 'enterprise';
type Theme = 'system' | 'light' | 'dark';

export default function SessionSetup({ onStart, loading, error }: SessionSetupProps) {
  const [mode, setMode] = useState<Mode | null>(null);
  const [apiToken, setApiToken] = useState('');
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [showSetupWizard, setShowSetupWizard] = useState(false);
  const [configuredProviders, setConfiguredProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [checkingConfig, setCheckingConfig] = useState(false);
  const [donkitConfigured, setDonkitConfigured] = useState(false);
  const [theme, setTheme] = useState<Theme>('system');

  const { getProviders } = useSettings();

  // Load configured providers (for both modes)
  useEffect(() => {
    loadProviders();
  }, []);

  // Apply UI colour scheme (same logic as portal Profile)
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') {
      const m = window.matchMedia?.('(prefers-color-scheme: dark)');
      if (!m) return;
      const apply = () => {
        if (m.matches) {
          root.removeAttribute('data-theme');
        } else {
          root.setAttribute('data-theme', 'light');
        }
      };
      apply();
      m.addEventListener('change', apply);
      return () => m.removeEventListener('change', apply);
    }
    root.setAttribute('data-theme', theme);
  }, [theme]);

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

  const handleCopyHelpCommand = () => {
    const command = 'donkit-ragops --help';
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(command).catch((err) => {
        console.error('Failed to copy help command:', err);
      });
    }
  };

  const handleStart = async () => {
    if (!mode) {
      return;
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
    setShowSetupWizard(false);

    if (newMode === 'saas') {
      // Immediately show API token input for SaaS mode
      setShowTokenInput(true);
    } else {
      setShowTokenInput(false);
      setApiToken('');
    }
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
    <div className="min-h-screen flex flex-col" style={{ 
      paddingTop: 'var(--page-padding-vert)',
      paddingBottom: 'var(--space-l)',
      paddingLeft: 'var(--page-padding-hor)',
      paddingRight: 'var(--page-padding-hor)',
      backgroundColor: 'var(--color-bg)'
    }}>
      <div className="flex-1 flex items-center justify-center">
        <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center" style={{ marginBottom: 0 }}>
          <div
            className="flex items-center justify-center"
            style={{ gap: 'var(--space-s)', marginBottom: 'var(--space-l)' }}
          >
            <img
              src={DonkitIcon}
              alt="Donkit"
              width={40}
              height={40}
              style={{ borderRadius: 'var(--space-s)' }}
            />
            <h1 className="h1" style={{ marginBottom: 0 }}>RAGOps Agent</h1>
          </div>
          <h3 className="h3" style={{ marginBottom: 'var(--space-m)', color: 'var(--color-txt-icon-2)' }}>
            Choose your operating mode to get started:
          </h3>
        </div>

        {/* Mode Selection */}
        <div className="grid grid-cols-3" style={{ gap: 'var(--space-m)', marginBottom: 'var(--space-l)' }}>
          {/* Local Mode */}
          <button
            onClick={() => handleModeChange('local')}
            style={{
              padding: 'var(--space-l)',
              borderRadius: 'var(--space-s)',
              border: '1px solid var(--color-border)',
              backgroundColor: mode === 'local' ? 'var(--color-action-item-selected)' : 'transparent',
              transition: 'background-color 0.2s ease, border-color 0.2s ease',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-action-item-hover)';
              e.currentTarget.style.borderColor = 'var(--color-border-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = mode === 'local'
                ? 'var(--color-action-item-selected)'
                : 'transparent';
              e.currentTarget.style.borderColor = 'var(--color-border)';
            }}
          >
            <div className="flex flex-col items-center text-center h-full">
              <img
                src={LocalModeIcon}
                alt=""
                className="icon-txt1"
                style={{
                  width: '48px',
                  height: '48px',
                  marginBottom: 'var(--space-m)',
                }}
              />
              <h3 className="h4" style={{ marginBottom: 'var(--space-xs)', fontWeight: 500 }}>Local</h3>
              <p className="p2">
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
                    <span
                      className="inline-flex items-center gap-1 px-2 py-1"
                      style={{
                        backgroundColor: 'var(--color-action-item-selected)',
                        color: 'var(--color-txt-icon-1)',
                        borderRadius: 'var(--space-xs)',
                      }}
                    >
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
            style={{
              padding: 'var(--space-l)',
              borderRadius: 'var(--space-s)',
              border: '1px solid var(--color-border)',
              backgroundColor: mode === 'saas' ? 'var(--color-action-item-selected)' : 'transparent',
              transition: 'background-color 0.2s ease, border-color 0.2s ease',
              height: '100%'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-action-item-hover)';
              e.currentTarget.style.borderColor = 'var(--color-border-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = mode === 'saas'
                ? 'var(--color-action-item-selected)'
                : 'transparent';
              e.currentTarget.style.borderColor = 'var(--color-border)';
            }}
          >
            <div className="flex flex-col items-center text-center h-full">
              <img
                src={SaaSModeIcon}
                alt=""
                className="icon-txt1"
                style={{
                  width: '48px',
                  height: '48px',
                  marginBottom: 'var(--space-m)',
                }}
              />
              <h3 className="h4" style={{ marginBottom: 'var(--space-xs)', fontWeight: 500 }}>SaaS</h3>
              <p className="p2">
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
                    <span
                      className="inline-flex items-center gap-1 px-2 py-1"
                      style={{
                        backgroundColor: 'var(--color-action-item-selected)',
                        color: 'var(--color-txt-icon-1)',
                        borderRadius: 'var(--space-xs)',
                      }}
                    >
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
          <div
            style={{
              padding: 'var(--space-l)',
              borderRadius: 'var(--space-s)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'transparent',
              opacity: 0.5,
              cursor: 'not-allowed',
              height: '100%'
            }}
          >
            <div className="flex flex-col items-center text-center h-full" style={{ opacity: 1, cursor: 'default' }}>
              <img
                src={EnterpriseModeIcon}
                alt=""
                className="icon-txt1"
                style={{
                  width: '48px',
                  height: '48px',
                  marginBottom: 'var(--space-m)',
                }}
              />
              <h3 className="h4" style={{ marginBottom: 'var(--space-xs)', fontWeight: 500 }}>Enterprise</h3>
              <p className="p2">
                Deploy locally on-premises or within your corporate VPC
              </p>
              <div className="flex-1" />
              <div className="pt-4 text-xs">
                <a
                  href="https://donkit.ai/?utm_source=app"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary"
                  style={{
                    fontSize: 'var(--font-size-p2)',
                    padding: 'var(--space-xs) var(--space-m)',
                    cursor: 'pointer',
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  Contact Us
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Provider selection for Local Mode */}
        {mode === 'local' && configuredProviders.length > 0 && !checkingConfig && (
          <div style={{ 
            marginBottom: 'var(--space-l)', 
            backgroundColor: 'transparent', 
            borderRadius: 'var(--space-s)', 
            padding: 'var(--space-l)', 
            border: '1px solid var(--color-border)' 
          }}>
            <h3 className="p2" style={{ fontWeight: 500, marginBottom: 'var(--space-m)' }}>Select Provider</h3>
            <div className="space-y-2">
              {configuredProviders.map((provider) => {
                const isSelected = selectedProvider === provider.name;
                return (
                  <button
                    key={provider.name}
                    onClick={() => setSelectedProvider(provider.name)}
                    className="w-full text-left"
                    style={{
                      padding: 'var(--space-m)',
                      borderRadius: 'var(--space-xs)',
                      border: '1px solid var(--color-border)',
                      backgroundColor: isSelected ? 'var(--color-action-item-selected)' : 'transparent',
                      color: 'var(--color-txt-icon-1)',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--color-action-item-hover)';
                      e.currentTarget.style.borderColor = 'var(--color-border-hover)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = isSelected
                        ? 'var(--color-action-item-selected)'
                        : 'transparent';
                      e.currentTarget.style.borderColor = 'var(--color-border)';
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div style={{ fontWeight: 500, color: 'var(--color-txt-icon-1)' }}>
                          {provider.display_name}
                        </div>
                        <div style={{ fontSize: 'var(--font-size-p2)', color: 'var(--color-txt-icon-2)', marginTop: 'var(--space-xs)' }}>
                          {provider.description}
                        </div>
                      </div>
                      {isSelected && (
                        <CheckCircle2 className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--color-txt-icon-1)' }} />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Configuration hint for Local Mode */}
        {mode === 'local' && configuredProviders.length === 0 && !checkingConfig && (
          <div style={{ 
            marginBottom: 'var(--space-l)', 
            padding: 'var(--space-m)', 
            backgroundColor: 'transparent', 
            border: '1px solid var(--color-border)', 
            borderRadius: 'var(--space-s)', 
            display: 'flex',
            alignItems: 'flex-start',
            gap: 'var(--space-m)',
          }}>
            <img
              src={AlertIcon}
              alt=""
              className="icon-txt2"
              style={{
                width: 24,
                height: 24,
                marginTop: 2,
                flexShrink: 0,
              }}
            />
            <p className="p2">
              <strong>First time setup:</strong> You'll need to configure at least one LLM provider (OpenAI, Vertex AI, etc.) before starting.
              Click "Setup Provider" below to get started.
            </p>
          </div>
        )}

        {/* API Token Input (SaaS only) */}
        {mode === 'saas' && showTokenInput && (
          <div style={{ 
            marginBottom: 'var(--space-l)', 
            backgroundColor: 'transparent', 
            borderRadius: 'var(--space-s)', 
            padding: 'var(--space-l)', 
            border: '1px solid var(--color-border)' 
          }}>
            <label className="block" style={{ marginBottom: 'var(--space-s)' }}>
              <div className="flex items-center gap-2 p2" style={{ fontWeight: 500, marginBottom: 'var(--space-s)' }}>
                <Key className="w-4 h-4" />
                API Token (optional)
              </div>
              <input
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="Enter your API token or leave empty to use saved token"
                style={{
                  width: '100%',
                  padding: 'var(--space-s) var(--space-m)',
                  backgroundColor: 'transparent',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--space-s)',
                  color: 'var(--color-txt-icon-1)',
                  fontFamily: 'inherit',
                  fontSize: 'var(--font-size-p1)',
                  transition: 'border-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  if (!e.currentTarget.matches(':focus')) {
                    e.currentTarget.style.borderColor = 'var(--color-border-hover)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!e.currentTarget.matches(':focus')) {
                    e.currentTarget.style.borderColor = 'var(--color-border)';
                  }
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--color-border-hover)';
                  e.target.style.outline = 'none';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--color-border)';
                }}
              />
            </label>
            <p className="p2" style={{ marginTop: 'var(--space-s)', color: 'var(--color-txt-icon-2)' }}>
              If you've already logged in via CLI (<code className="bg-dark-bg px-2 py-0.5 rounded">donkit-ragops login</code>), you can
              leave this empty.
            </p>
          </div>
        )}

        {/* Error Message */}
        {mode && error && (
          <div style={{ 
            marginBottom: 'var(--space-l)', 
            padding: 'var(--space-m)', 
            backgroundColor: 'rgba(234, 100, 100, 0.1)', 
            border: '1px solid rgba(234, 100, 100, 0.3)', 
            borderRadius: 'var(--space-s)' 
          }}>
            <p className="p2" style={{ color: 'var(--color-accent)' }}>{error}</p>
          </div>
        )}

        {/* Start Button (primary, accent red) – only after mode is selected */}
        {mode && (
          <button
            onClick={handleStart}
            disabled={loading || checkingConfig}
            className="btn-primary btn-primary--full"
          >
            {loading || checkingConfig ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {checkingConfig ? 'Checking configuration...' : 'Starting...'}
              </>
            ) : (
              <>
                {mode === 'local' && configuredProviders.length === 0 ? (
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
        )}

        {/* Add/Manage providers button for local mode */}
        {mode === 'local' && (
          <button
            onClick={handleAddProvider}
            disabled={loading || checkingConfig}
            className="w-full flex items-center justify-center transition-colors"
            style={{
              marginTop: 'var(--space-m)',
              padding: 'var(--space-s) 0',
              fontSize: 'var(--font-size-p2)',
              color: 'var(--color-txt-icon-2)',
              gap: 'var(--space-s)'
            }}
            onMouseEnter={(e) => {
              if (!loading && !checkingConfig) {
                e.currentTarget.style.color = 'var(--color-txt-icon-1)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--color-txt-icon-2)';
            }}
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
            className="w-full flex items-center justify-center transition-colors"
            style={{
              marginTop: 'var(--space-m)',
              padding: 'var(--space-s) 0',
              fontSize: 'var(--font-size-p2)',
              color: 'var(--color-txt-icon-2)',
              gap: 'var(--space-s)'
            }}
            onMouseEnter={(e) => {
              if (!loading && !checkingConfig) {
                e.currentTarget.style.color = 'var(--color-txt-icon-1)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--color-txt-icon-2)';
            }}
          >
            <Key className="w-4 h-4" />
            Use a different API key
          </button>
        )}

        </div>
      </div>

      {/* Info Footer - fixed to bottom */}
      <div className="w-full flex justify-center">
        <div className="max-w-2xl w-full"
          style={{
            marginTop: 'var(--space-xl)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-start',
            gap: 'var(--space-l)',
            flexWrap: 'wrap',
          }}
        >
          {/* Help command block */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              gap: 'var(--space-xs)',
            }}
          >
            <span className="p2" style={{ color: 'var(--color-txt-icon-2)' }}>
              Need help?
            </span>
            <div
              style={{
                position: 'relative',
                maxWidth: '100%',
              }}
            >
              <code
                style={{
                  display: 'block',
                  backgroundColor: 'var(--color-action-item-selected)',
                  border: '1px solid var(--color-border)',
                  padding: 'var(--space-xs) var(--space-xl) var(--space-xs) var(--space-s)',
                  borderRadius: 'var(--space-xs)',
                  fontFamily: 'inherit',
                  fontSize: 'var(--font-size-p2)',
                  color: 'var(--color-txt-icon-2)',
                }}
              >
                donkit-ragops --help
              </code>
              <button
                type="button"
                onClick={handleCopyHelpCommand}
                aria-label="Copy help command"
                title="Copy help command"
                style={{
                  position: 'absolute',
                  right: '4px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: '24px',
                  height: '24px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: 'none',
                  borderRadius: '50%',
                  backgroundColor: 'transparent',
                  color: 'var(--color-txt-icon-2)',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-txt-icon-1)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-txt-icon-2)';
                }}
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* UI colour scheme (copied from portal Profile) */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              gap: 'var(--space-xs)',
            }}
          >
            <span
              className="p2"
              style={{
                fontWeight: 300,
                color: 'var(--color-txt-icon-2)',
              }}
            >
              UI colour scheme
            </span>
            <div
              className="flex items-center"
              role="group"
              aria-label="UI colour scheme"
              style={{ gap: 'var(--space-xs)' }}
            >
              <button
                type="button"
                onClick={() => setTheme('system')}
                aria-pressed={theme === 'system'}
                style={{
                  width: 40,
                  height: 40,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                  borderRadius: 'var(--space-xs)',
                  border: '1px solid var(--color-border)',
                  backgroundColor:
                    theme === 'system' ? 'var(--color-action-item-selected)' : 'transparent',
                  color: 'var(--color-txt-icon-1)',
                  cursor: 'pointer',
                  transition:
                    'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                }}
                title="System"
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    'var(--color-action-item-hover)';
                  (e.currentTarget as HTMLButtonElement).style.borderColor =
                    'var(--color-border-hover)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    theme === 'system' ? 'var(--color-action-item-selected)' : 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.borderColor =
                    'var(--color-border)';
                }}
              >
                <img
                  src={ThemeSystemIcon}
                  alt=""
                  className="icon-txt1"
                  style={{ width: 24, height: 24 }}
                />
              </button>
              <button
                type="button"
                onClick={() => setTheme('light')}
                aria-pressed={theme === 'light'}
                style={{
                  width: 40,
                  height: 40,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                  borderRadius: 'var(--space-xs)',
                  border: '1px solid var(--color-border)',
                  backgroundColor:
                    theme === 'light' ? 'var(--color-action-item-selected)' : 'transparent',
                  color: 'var(--color-txt-icon-1)',
                  cursor: 'pointer',
                  transition:
                    'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                }}
                title="Light"
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    'var(--color-action-item-hover)';
                  (e.currentTarget as HTMLButtonElement).style.borderColor =
                    'var(--color-border-hover)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    theme === 'light' ? 'var(--color-action-item-selected)' : 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.borderColor =
                    'var(--color-border)';
                }}
              >
                <img
                  src={ThemeLightIcon}
                  alt=""
                  className="icon-txt1"
                  style={{ width: 24, height: 24 }}
                />
              </button>
              <button
                type="button"
                onClick={() => setTheme('dark')}
                aria-pressed={theme === 'dark'}
                style={{
                  width: 40,
                  height: 40,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                  borderRadius: 'var(--space-xs)',
                  border: '1px solid var(--color-border)',
                  backgroundColor:
                    theme === 'dark' ? 'var(--color-action-item-selected)' : 'transparent',
                  color: 'var(--color-txt-icon-1)',
                  cursor: 'pointer',
                  transition:
                    'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
                }}
                title="Dark"
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    'var(--color-action-item-hover)';
                  (e.currentTarget as HTMLButtonElement).style.borderColor =
                    'var(--color-border-hover)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    theme === 'dark' ? 'var(--color-action-item-selected)' : 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.borderColor =
                    'var(--color-border)';
                }}
              >
                <img
                  src={ThemeDarkIcon}
                  alt=""
                  className="icon-txt1"
                  style={{ width: 24, height: 24 }}
                />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
