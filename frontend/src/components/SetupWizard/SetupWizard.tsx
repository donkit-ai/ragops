/**
 * Setup Wizard for configuring LLM providers
 */

import { useState, useEffect } from 'react';
import { ArrowLeft, Check, Loader2, Plus } from 'lucide-react';
import { useSettings } from '../../hooks/useSettings';
import type { ProviderInfo } from '../../types/settings';
import ProviderSelection from './ProviderSelection';
import ProviderConfigForm from './ProviderConfigForm';

interface SetupWizardProps {
  onComplete: () => void;
  onBack?: () => void;
}

type WizardStep = 'select' | 'configure' | 'test' | 'save' | 'success';

export default function SetupWizard({ onComplete, onBack }: SetupWizardProps) {
  const [step, setStep] = useState<WizardStep>('select');
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<ProviderInfo | null>(null);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const { loading, getProviders, testProvider, saveProvider } = useSettings();

  // Load providers on mount
  useEffect(() => {
    const loadProviders = async () => {
      try {
        const response = await getProviders();
        setProviders(response.providers);
      } catch (err) {
        console.error('Failed to load providers:', err);
      }
    };
    loadProviders();
  }, [getProviders]);

  const handleProviderSelect = (provider: ProviderInfo) => {
    setSelectedProvider(provider);
    setConfig({});
    setTestResult(null);
    setStep('configure');
  };

  const handleConfigSubmit = async (newConfig: Record<string, string>) => {
    if (!selectedProvider) return;

    setConfig(newConfig);
    setStep('test');

    // Test credentials
    try {
      const result = await testProvider({
        provider: selectedProvider.name,
        config: newConfig,
      });

      setTestResult(result);

      if (result.success) {
        // Auto-advance to save step
        setTimeout(() => {
          handleSave(newConfig);
        }, 1000);
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : 'Failed to test credentials',
      });
    }
  };

  const handleSave = async (configToSave?: Record<string, string>) => {
    if (!selectedProvider) return;

    setStep('save');
    const finalConfig = configToSave || config;

    try {
      await saveProvider({
        provider: selectedProvider.name,
        config: finalConfig,
      });

      // Success - show success screen
      setTimeout(() => {
        setStep('success');
      }, 1000);
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : 'Failed to save configuration',
      });
      setStep('test');
    }
  };

  const handleAddAnother = () => {
    // Reset to select step to add another provider
    setStep('select');
    setSelectedProvider(null);
    setConfig({});
    setTestResult(null);
  };

  const handleDone = () => {
    onComplete();
  };

  const handleBack = () => {
    if (step === 'configure') {
      setStep('select');
      setSelectedProvider(null);
    } else if (step === 'test') {
      setStep('configure');
      setTestResult(null);
    } else if (onBack) {
      onBack();
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ 
      padding: 'var(--page-padding-vert) var(--page-padding-hor)',
      backgroundColor: 'var(--color-bg)'
    }}>
      <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center" style={{ marginBottom: 'var(--space-xl)' }}>
          <h1 className="h1" style={{ marginBottom: 'var(--space-s)' }}>Setup LLM Provider</h1>
          <p className="p1" style={{ color: 'var(--color-txt-icon-2)' }}>
            {step === 'select' && 'Choose your preferred LLM provider'}
            {step === 'configure' && `Configure ${selectedProvider?.display_name || 'provider'}`}
            {step === 'test' && 'Testing credentials...'}
            {step === 'save' && 'Saving configuration...'}
            {step === 'success' && 'Provider configured successfully!'}
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="flex items-center justify-center" style={{ gap: 'var(--space-s)', marginBottom: 'var(--space-xl)' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: step === 'select' ? 'var(--color-white-60)' : 'var(--color-border)' }} />
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: step === 'configure' ? 'var(--color-white-60)' : 'var(--color-border)' }} />
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: (step === 'test' || step === 'save' || step === 'success') ? 'var(--color-white-60)' : 'var(--color-border)' }} />
        </div>

        {/* Content */}
        <div style={{ 
          backgroundColor: 'var(--color-action-item-selected)', 
          borderRadius: 'var(--space-s)', 
          padding: 'var(--space-l)', 
          border: '1px solid var(--color-border)' 
        }}>
          {step === 'select' && (
            <ProviderSelection
              providers={providers}
              onSelect={handleProviderSelect}
            />
          )}

          {step === 'configure' && selectedProvider && (
            <ProviderConfigForm
              provider={selectedProvider}
              initialConfig={config}
              onSubmit={handleConfigSubmit}
              onBack={handleBack}
            />
          )}

          {step === 'test' && (
            <div className="text-center" style={{ padding: 'var(--space-xl) 0' }}>
              {testResult ? (
                testResult.success ? (
                  <div className="flex flex-col items-center" style={{ gap: 'var(--space-m)' }}>
                    <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: 'rgba(0, 200, 110, 0.1)' }}>
                      <Check className="w-8 h-8" style={{ color: 'var(--color-success)' }} />
                    </div>
                    <h3 className="h3" style={{ fontWeight: 500 }}>Credentials Valid</h3>
                    <p className="p1" style={{ color: 'var(--color-txt-icon-2)' }}>{testResult.message}</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center" style={{ gap: 'var(--space-m)' }}>
                    <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: 'rgba(234, 100, 100, 0.1)' }}>
                      <span style={{ fontSize: '24px', color: 'var(--color-accent)' }}>✕</span>
                    </div>
                    <h3 className="h3" style={{ fontWeight: 500 }}>Validation Failed</h3>
                    <p style={{ color: 'var(--color-accent)' }}>{testResult.message}</p>
                    <button
                      onClick={handleBack}
                      className="transition-colors"
                      style={{
                        marginTop: 'var(--space-m)',
                        padding: 'var(--space-s) var(--space-l)',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-txt-icon-1)',
                        borderRadius: 'var(--space-s)'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-border)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg)'}
                    >
                      Go Back
                    </button>
                  </div>
                )
              ) : (
                <div className="flex flex-col items-center" style={{ gap: 'var(--space-m)' }}>
                  <Loader2 className="w-12 h-12 animate-spin" style={{ color: 'var(--color-white-60)' }} />
                  <h3 className="h3" style={{ fontWeight: 500 }}>Testing Credentials</h3>
                  <p className="p1" style={{ color: 'var(--color-txt-icon-2)' }}>Please wait...</p>
                </div>
              )}
            </div>
          )}

          {step === 'save' && (
            <div className="text-center" style={{ padding: 'var(--space-xl) 0' }}>
              <div className="flex flex-col items-center" style={{ gap: 'var(--space-m)' }}>
                <Loader2 className="w-12 h-12 animate-spin" style={{ color: 'var(--color-white-60)' }} />
                <h3 className="h3" style={{ fontWeight: 500 }}>Saving Configuration</h3>
                <p className="p1" style={{ color: 'var(--color-txt-icon-2)' }}>Almost done...</p>
              </div>
            </div>
          )}

          {step === 'success' && selectedProvider && (
            <div className="text-center" style={{ padding: 'var(--space-xl) 0' }}>
              <div className="flex flex-col items-center" style={{ gap: 'var(--space-m)', marginBottom: 'var(--space-l)' }}>
                <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ backgroundColor: 'rgba(0, 200, 110, 0.1)' }}>
                  <Check className="w-8 h-8" style={{ color: 'var(--color-success)' }} />
                </div>
                <h3 className="h3" style={{ fontWeight: 500 }}>Provider Configured!</h3>
                <p className="p1" style={{ color: 'var(--color-txt-icon-2)' }}>
                  {selectedProvider.display_name} has been successfully configured.
                </p>
              </div>

              <div className="flex" style={{ gap: 'var(--space-m)' }}>
                <button
                  onClick={handleAddAnother}
                  className="btn-secondary flex-1 justify-center"
                >
                  <Plus className="w-4 h-4" />
                  Add Another Provider
                </button>
                <button
                  onClick={handleDone}
                  className="btn-primary flex-1 justify-center"
                >
                  Done
                  <Check className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Back Button - only show on select step if onBack is provided */}
        {step === 'select' && onBack && (
          <button
            onClick={handleBack}
            disabled={loading}
            className="flex items-center transition-colors"
            style={{
              marginTop: 'var(--space-m)',
              gap: 'var(--space-s)',
              color: 'var(--color-txt-icon-2)'
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.color = 'var(--color-txt-icon-1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--color-txt-icon-2)';
            }}
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        )}
      </div>
    </div>
  );
}
