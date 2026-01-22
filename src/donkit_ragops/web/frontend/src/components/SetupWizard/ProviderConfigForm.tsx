/**
 * Dynamic configuration form for provider credentials
 */

import { useState } from 'react';
import { ArrowRight, ArrowLeft, Eye, EyeOff, HelpCircle } from 'lucide-react';
import type { ProviderInfo, ProviderField } from '../../types/settings';

interface ProviderConfigFormProps {
  provider: ProviderInfo;
  initialConfig?: Record<string, string>;
  onSubmit: (config: Record<string, string>) => void;
  onBack: () => void;
}

export default function ProviderConfigForm({
  provider,
  initialConfig = {},
  onSubmit,
  onBack,
}: ProviderConfigFormProps) {
  const [config, setConfig] = useState<Record<string, string>>(initialConfig);
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (fieldName: string, value: string) => {
    setConfig((prev) => ({ ...prev, [fieldName]: value }));
    // Clear error when user starts typing
    if (errors[fieldName]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[fieldName];
        return newErrors;
      });
    }
  };

  const togglePasswordVisibility = (fieldName: string) => {
    setShowPassword((prev) => ({ ...prev, [fieldName]: !prev[fieldName] }));
  };

  const validateField = (field: ProviderField, value: string): string | null => {
    if (field.required && !value) {
      return `${field.label} is required`;
    }

    if (field.validation_pattern && value) {
      const regex = new RegExp(field.validation_pattern);
      if (!regex.test(value)) {
        return `Invalid format for ${field.label}`;
      }
    }

    return null;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate all fields
    const newErrors: Record<string, string> = {};
    for (const field of provider.fields) {
      const value = config[field.name] || '';
      const error = validateField(field, value);
      if (error) {
        newErrors[field.name] = error;
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Submit config
    onSubmit(config);
  };

  const renderField = (field: ProviderField) => {
    const value = config[field.name] || '';
    const error = errors[field.name];
    const isPassword = field.type === 'password';
    const showValue = isPassword && showPassword[field.name];

    return (
      <div key={field.name} className="mb-4">
        <label className="block mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-dark-text-primary">
              {field.label}
              {!field.required && <span className="text-dark-text-muted ml-1">(optional)</span>}
            </span>
            {field.help_text && (
              <div className="group relative">
                <HelpCircle className="w-4 h-4 text-dark-text-muted cursor-help" />
                <div className="absolute left-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-dark-bg border border-dark-border rounded-lg text-xs text-dark-text-secondary z-10">
                  {field.help_text}
                </div>
              </div>
            )}
          </div>

          <div className="relative">
            <input
              type={isPassword && !showValue ? 'password' : 'text'}
              value={value}
              onChange={(e) => handleChange(field.name, e.target.value)}
              placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
              className={`
                w-full px-4 py-2.5 bg-dark-bg border rounded-lg text-dark-text-primary
                placeholder:text-dark-text-muted
                focus:ring-2 focus:ring-accent-blue focus:border-transparent
                ${error ? 'border-accent-red' : 'border-dark-border'}
                ${isPassword ? 'pr-12' : ''}
              `}
            />
            {isPassword && (
              <button
                type="button"
                onClick={() => togglePasswordVisibility(field.name)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-text-muted hover:text-dark-text-primary"
              >
                {showValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            )}
          </div>

          {error && (
            <p className="text-xs text-accent-red mt-1">{error}</p>
          )}
        </label>
      </div>
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Provider info */}
      <div className="mb-6 p-4 bg-dark-bg rounded-lg border border-dark-border">
        <h3 className="font-semibold text-dark-text-primary mb-1">{provider.display_name}</h3>
        <p className="text-sm text-dark-text-secondary mb-2">{provider.description}</p>
        {provider.documentation_url && (
          <a
            href={provider.documentation_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-accent-blue hover:underline"
          >
            Get API key →
          </a>
        )}
      </div>

      {/* Dynamic fields */}
      <div className="space-y-4">
        {provider.fields.map(renderField)}
      </div>

      {/* Embeddings warning */}
      {!provider.has_embeddings && (
        <div className="p-3 bg-accent-orange/10 border border-accent-orange/30 rounded-lg">
          <p className="text-sm text-accent-orange">
            <strong>Note:</strong> {provider.display_name} doesn't support embeddings. You'll need to
            configure a separate embeddings provider after this step.
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2 px-6 py-3 bg-dark-bg hover:bg-dark-border text-dark-text-primary rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          type="submit"
          className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-accent-blue hover:bg-accent-blue-hover text-white font-semibold rounded-lg transition-colors"
        >
          Test & Save
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
