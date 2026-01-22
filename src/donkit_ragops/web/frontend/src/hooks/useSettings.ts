/**
 * Hook for managing provider settings
 */

import { useCallback, useState } from 'react';
import type {
  ProvidersListResponse,
  CurrentSettingsResponse,
  ProviderTestRequest,
  ProviderTestResponse,
  ProviderSaveRequest,
  ProviderSaveResponse,
} from '../types/settings';

const API_BASE = '/api/v1';

export function useSettings() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getProviders = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/settings/providers`);
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to fetch providers');
      }
      return (await response.json()) as ProvidersListResponse;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getCurrentSettings = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/settings/current`);
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to fetch current settings');
      }
      return (await response.json()) as CurrentSettingsResponse;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const testProvider = useCallback(async (request: ProviderTestRequest) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/settings/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to test provider credentials');
      }

      return (await response.json()) as ProviderTestResponse;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const saveProvider = useCallback(async (request: ProviderSaveRequest) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/settings/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save provider configuration');
      }

      return (await response.json()) as ProviderSaveResponse;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    getProviders,
    getCurrentSettings,
    testProvider,
    saveProvider,
  };
}
