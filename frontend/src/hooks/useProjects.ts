import { useState, useEffect, useCallback } from 'react';

const DEFAULT_PROJECTS_LIMIT = 100;

export interface Project {
  id: string;
  created_at?: string;
  updated_at?: string;
  message_count: number;
  status?: string;
  rag_use_case?: string;
}

interface UseProjectsReturn {
  projects: Project[];
  loading: boolean;
  error: string | null;
  refreshProjects: () => Promise<void>;
}

export function useProjects(sessionId: string | null): UseProjectsReturn {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = useCallback(async () => {
    if (!sessionId) {
      setProjects([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/projects/recent?session_id=${sessionId}&limit=${DEFAULT_PROJECTS_LIMIT}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch projects: ${response.statusText}`);
      }

      const data = await response.json();
      setProjects(data.projects || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch projects';
      setError(message);
      console.error('Error fetching projects:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return {
    projects,
    loading,
    error,
    refreshProjects: fetchProjects,
  };
}
