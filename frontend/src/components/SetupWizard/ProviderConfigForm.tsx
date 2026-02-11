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
      <div key={field.name} style={{ marginBottom: 'var(--space-m)' }}>
        <label className="block" style={{ marginBottom: 'var(--space-s)' }}>
          <div className="flex items-center" style={{ gap: 'var(--space-s)', marginBottom: 'var(--space-xs)' }}>
            <span className="p2" style={{ fontWeight: 500 }}>
              {field.label}
              {!field.required && <span style={{ marginLeft: 'var(--space-xs)', color: 'var(--color-txt-icon-2)' }}>(optional)</span>}
            </span>
            {field.help_text && (
              <div className="group relative">
                <HelpCircle className="w-4 h-4 cursor-help" style={{ color: 'var(--color-txt-icon-2)' }} />
                <div className="absolute left-0 bottom-full hidden group-hover:block z-10" style={{ 
                  marginBottom: 'var(--space-s)', 
                  width: '256px', 
                  padding: 'var(--space-s)', 
                  backgroundColor: 'var(--color-bg)', 
                  border: '1px solid var(--color-border)', 
                  borderRadius: 'var(--space-s)', 
                  fontSize: 'var(--font-size-p2)', 
                  color: 'var(--color-txt-icon-2)' 
                }}>
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
              style={{
                width: '100%',
                padding: 'var(--space-s) var(--space-m)',
                backgroundColor: 'transparent',
                border: `1px solid ${error ? 'var(--color-accent)' : 'var(--color-border)'}`,
                borderRadius: 'var(--space-s)',
                color: 'var(--color-txt-icon-1)',
                fontFamily: 'inherit',
                fontSize: 'var(--font-size-p1)',
                paddingRight: isPassword ? '48px' : undefined,
                transition: 'border-color 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (!error && !e.currentTarget.matches(':focus')) {
                  e.currentTarget.style.borderColor = 'var(--color-border-hover)';
                }
              }}
              onMouseLeave={(e) => {
                if (!error && !e.currentTarget.matches(':focus')) {
                  e.currentTarget.style.borderColor = 'var(--color-border)';
                }
              }}
              onFocus={(e) => {
                if (!error) {
                  e.target.style.borderColor = 'var(--color-border-hover)';
                }
                e.target.style.outline = 'none';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = error ? 'var(--color-accent)' : 'var(--color-border)';
              }}
            />
            {isPassword && (
              <button
                type="button"
                onClick={() => togglePasswordVisibility(field.name)}
                className="absolute top-1/2 -translate-y-1/2"
                style={{ right: '12px', color: 'var(--color-txt-icon-2)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-txt-icon-1)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-txt-icon-2)'}
              >
                {showValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            )}
          </div>

          {error && (
            <p className="p2" style={{ marginTop: 'var(--space-xs)', color: 'var(--color-accent)' }}>{error}</p>
          )}
        </label>
      </div>
    );
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-m)' }}>
      {/* Provider info */}
      <div style={{ 
        marginBottom: 'var(--space-l)', 
        padding: 'var(--space-m)', 
        backgroundColor: 'var(--color-bg)', 
        borderRadius: 'var(--space-s)', 
        border: '1px solid var(--color-border)' 
      }}>
        <h3 className="h4" style={{ fontWeight: 500, marginBottom: 'var(--space-xs)' }}>{provider.display_name}</h3>
        <p className="p2" style={{ marginBottom: 'var(--space-s)', color: 'var(--color-txt-icon-2)' }}>{provider.description}</p>
        {provider.documentation_url && (
          <a
            href={provider.documentation_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center"
            style={{ gap: 'var(--space-xs)', fontSize: 'var(--font-size-p2)', color: 'var(--color-white-60)' }}
            onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
            onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
          >
            Get API key →
          </a>
        )}
      </div>

      {/* Dynamic fields */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-m)' }}>
        {provider.fields.map(renderField)}
      </div>

      {/* Embeddings warning */}
      {!provider.has_embeddings && (
        <div style={{ 
          padding: 'var(--space-m)', 
          backgroundColor: 'rgba(255, 187, 0, 0.1)', 
          border: '1px solid rgba(255, 187, 0, 0.3)', 
          borderRadius: 'var(--space-s)' 
        }}>
          <p className="p2" style={{ color: 'var(--color-neutral)' }}>
            <strong>Note:</strong> {provider.display_name} doesn't support embeddings. You'll need to
            configure a separate embeddings provider after this step.
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex" style={{ gap: 'var(--space-m)', paddingTop: 'var(--space-m)' }}>
        <button
          type="button"
          onClick={onBack}
          className="btn-secondary"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          type="submit"
          className="btn-primary flex-1 justify-center"
        >
          Test & Save
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
