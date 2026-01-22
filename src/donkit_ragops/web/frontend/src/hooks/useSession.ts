import { useCallback, useRef, useState } from 'react';
import { Session } from '../types/protocol';

const API_BASE = '/api/v1';

interface CreateSessionOptions {
  provider?: string;
  model?: string;
  enterprise_mode?: boolean;
  api_token?: string;
  existing_project_id?: string;
}

export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const creatingRef = useRef(false);

  const createSession = useCallback(async (options?: CreateSessionOptions) => {
    // Prevent double creation
    if (creatingRef.current) return null;
    creatingRef.current = true;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(options || {}),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create session');
      }

      const data = await response.json();

      // Fetch full session info
      const sessionResponse = await fetch(`${API_BASE}/sessions/${data.session_id}`);
      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        setSession(sessionData);
        return sessionData;
      }

      // Fallback to basic info
      const basicSession: Session = {
        id: data.session_id,
        provider: data.provider,
        model: data.model,
        created_at: Date.now() / 1000,
        last_activity: Date.now() / 1000,
        is_connected: false,
        message_count: 0,
        mcp_initialized: false,
      };
      setSession(basicSession);
      return basicSession;
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      setError(message);
      throw e;
    } finally {
      setLoading(false);
      creatingRef.current = false;
    }
  }, []);

  const deleteSession = useCallback(async () => {
    if (!session) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/sessions/${session.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete session');
      }

      setSession(null);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      setError(message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [session]);

  const refreshSession = useCallback(async () => {
    if (!session) return;

    try {
      const response = await fetch(`${API_BASE}/sessions/${session.id}`);
      if (response.ok) {
        const data = await response.json();
        setSession(data);
      }
    } catch (e) {
      console.error('Failed to refresh session:', e);
    }
  }, [session]);

  return {
    session,
    loading,
    error,
    createSession,
    deleteSession,
    refreshSession,
  };
}
