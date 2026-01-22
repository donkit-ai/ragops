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
    <div className="min-h-screen bg-gradient-to-br from-dark-bg to-dark-surface flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-dark-text-primary mb-2">Setup LLM Provider</h1>
          <p className="text-dark-text-secondary">
            {step === 'select' && 'Choose your preferred LLM provider'}
            {step === 'configure' && `Configure ${selectedProvider?.display_name || 'provider'}`}
            {step === 'test' && 'Testing credentials...'}
            {step === 'save' && 'Saving configuration...'}
            {step === 'success' && 'Provider configured successfully!'}
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className={`w-3 h-3 rounded-full ${step === 'select' ? 'bg-accent-blue' : 'bg-dark-border'}`} />
          <div className={`w-3 h-3 rounded-full ${step === 'configure' ? 'bg-accent-blue' : 'bg-dark-border'}`} />
          <div className={`w-3 h-3 rounded-full ${step === 'test' || step === 'save' || step === 'success' ? 'bg-accent-blue' : 'bg-dark-border'}`} />
        </div>

        {/* Content */}
        <div className="bg-dark-surface rounded-xl p-6 border border-dark-border shadow-lg">
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
            <div className="text-center py-8">
              {testResult ? (
                testResult.success ? (
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-accent-green/10 flex items-center justify-center">
                      <Check className="w-8 h-8 text-accent-green" />
                    </div>
                    <h3 className="text-lg font-semibold text-dark-text-primary">Credentials Valid</h3>
                    <p className="text-dark-text-secondary">{testResult.message}</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-accent-red/10 flex items-center justify-center">
                      <span className="text-2xl text-accent-red">✕</span>
                    </div>
                    <h3 className="text-lg font-semibold text-dark-text-primary">Validation Failed</h3>
                    <p className="text-accent-red">{testResult.message}</p>
                    <button
                      onClick={handleBack}
                      className="mt-4 px-6 py-2 bg-dark-bg hover:bg-dark-border text-dark-text-primary rounded-lg transition-colors"
                    >
                      Go Back
                    </button>
                  </div>
                )
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <Loader2 className="w-12 h-12 text-accent-blue animate-spin" />
                  <h3 className="text-lg font-semibold text-dark-text-primary">Testing Credentials</h3>
                  <p className="text-dark-text-secondary">Please wait...</p>
                </div>
              )}
            </div>
          )}

          {step === 'save' && (
            <div className="text-center py-8">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-12 h-12 text-accent-blue animate-spin" />
                <h3 className="text-lg font-semibold text-dark-text-primary">Saving Configuration</h3>
                <p className="text-dark-text-secondary">Almost done...</p>
              </div>
            </div>
          )}

          {step === 'success' && selectedProvider && (
            <div className="text-center py-8">
              <div className="flex flex-col items-center gap-4 mb-6">
                <div className="w-16 h-16 rounded-full bg-accent-green/10 flex items-center justify-center">
                  <Check className="w-8 h-8 text-accent-green" />
                </div>
                <h3 className="text-lg font-semibold text-dark-text-primary">Provider Configured!</h3>
                <p className="text-dark-text-secondary">
                  {selectedProvider.display_name} has been successfully configured.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleAddAnother}
                  className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-dark-bg hover:bg-dark-border text-dark-text-primary rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add Another Provider
                </button>
                <button
                  onClick={handleDone}
                  className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-accent-blue hover:bg-accent-blue-hover text-white font-semibold rounded-lg transition-colors"
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
            className="mt-4 flex items-center gap-2 text-dark-text-muted hover:text-dark-text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        )}
      </div>
    </div>
  );
}
