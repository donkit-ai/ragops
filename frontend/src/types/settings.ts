/**
 * Types for settings API
 */

export interface ProviderField {
  name: string;
  label: string;
  type: 'text' | 'password' | 'file';
  required: boolean;
  default?: string | null;
  placeholder?: string | null;
  help_text?: string | null;
  validation_pattern?: string | null;
}

export interface ProviderInfo {
  name: string;
  display_name: string;
  description: string;
  fields: ProviderField[];
  has_embeddings: boolean | 'default' | 'custom';
  is_configured: boolean;
  documentation_url?: string | null;
}

export interface ProvidersListResponse {
  providers: ProviderInfo[];
}

export interface CurrentSettingsResponse {
  current_provider: string | null;
  settings: Record<string, string>;
}

export interface ProviderTestRequest {
  provider: string;
  config: Record<string, string>;
}

export interface ProviderTestResponse {
  success: boolean;
  message: string;
  details?: Record<string, any> | null;
}

export interface ProviderSaveRequest {
  provider: string;
  config: Record<string, string>;
}

export interface ProviderSaveResponse {
  success: boolean;
  message: string;
  env_path?: string | null;
}
