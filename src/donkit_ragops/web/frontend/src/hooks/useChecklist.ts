import { useCallback, useState } from 'react';

const API_BASE = '/api/v1';

export interface ChecklistState {
  hasChecklist: boolean;
  content: string | null;
}

export function useChecklist(sessionId: string | null) {
  const [checklist, setChecklist] = useState<ChecklistState>({
    hasChecklist: false,
    content: null,
  });

  const fetchChecklist = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/sessions/${sessionId}/checklist`);
      if (response.ok) {
        const data = await response.json();
        setChecklist({
          hasChecklist: data.has_checklist,
          content: data.content,
        });
      }
    } catch (e) {
      console.error('Failed to fetch checklist:', e);
    }
  }, [sessionId]);

  const updateFromMessage = useCallback((content: string | null) => {
    setChecklist({
      hasChecklist: content !== null,
      content,
    });
  }, []);

  return {
    checklist,
    fetchChecklist,
    updateFromMessage,
  };
}
