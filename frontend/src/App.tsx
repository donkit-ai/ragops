import { useState } from 'react';
import { useSession } from './hooks/useSession';
import ChatContainer from './components/Chat/ChatContainer';
import Header from './components/Layout/Header';
import SessionSetup from './components/SessionSetup/SessionSetup';
import ProjectsSidebar from './components/Projects/ProjectsSidebar';

function App() {
  const { session, loading, error, createSession } = useSession();
  const [setupError, setSetupError] = useState<string | null>(null);
  const [currentApiToken, setCurrentApiToken] = useState<string | undefined>();

  const handleSessionStart = async (options: { enterprise_mode: boolean; api_token?: string }) => {
    setSetupError(null);
    try {
      // Save API token for future project switches
      if (options.api_token) {
        setCurrentApiToken(options.api_token);
      }
      await createSession(options);
    } catch (e) {
      setSetupError(e instanceof Error ? e.message : 'Failed to create session');
      throw e;
    }
  };

  const handleProjectSelect = async (projectId: string) => {
    // Don't reload the same project
    if (session?.project_id === projectId) return;

    const oldSessionId = session?.id;

    setSetupError(null);
    try {
      // Delete old session before creating new one
      // This ensures we don't have multiple sessions in memory with different project_id
      if (oldSessionId) {
        try {
          await fetch(`/api/v1/sessions/${oldSessionId}`, {
            method: 'DELETE',
          });
        } catch (deleteError) {
          console.warn('Failed to delete old session:', deleteError);
          // Continue anyway - creating new session is more important
        }
      }

      // Create new session connected to the selected project
      // This ensures clean state, proper WebSocket reconnection,
      // and updated system prompt with correct user info and project ID
      await createSession({
        enterprise_mode: true,
        api_token: currentApiToken,
        existing_project_id: projectId,
      });
    } catch (e) {
      setSetupError(e instanceof Error ? e.message : 'Failed to switch project');
      console.error('Failed to switch project:', e);
    }
  };

  const handleNewProject = async () => {
    if (!session) return;

    const oldSessionId = session.id;

    setSetupError(null);
    try {
      // Create a new project via the existing session
      const response = await fetch(`/api/v1/sessions/${oldSessionId}/new-project`, {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create new project');
      }

      const data = await response.json();
      console.log('Created new project:', data.project_id);

      // Delete old session before creating new one
      // This ensures we don't have multiple sessions in memory with different project_id
      try {
        await fetch(`/api/v1/sessions/${oldSessionId}`, {
          method: 'DELETE',
        });
      } catch (deleteError) {
        console.warn('Failed to delete old session:', deleteError);
        // Continue anyway - creating new session is more important
      }

      // Create a new session connected to the new project
      // This ensures clean state and proper WebSocket reconnection
      await createSession({
        enterprise_mode: true,
        api_token: currentApiToken,
        existing_project_id: data.project_id,
      });
    } catch (e) {
      setSetupError(e instanceof Error ? e.message : 'Failed to create new project');
      console.error('Failed to create new project:', e);
    }
  };

  // Show setup screen if no session yet
  if (!session) {
    return (
      <SessionSetup
        onStart={handleSessionStart}
        loading={loading}
        error={setupError || error}
      />
    );
  }

  // Session active - show chat
  const isEnterpriseMode = session.enterprise_mode === true;

  return (
    <div className="h-screen bg-dark-bg flex flex-col overflow-hidden">
      <Header provider={session.provider} model={session.model} />
      <div className="flex-1 min-h-0 overflow-hidden flex">
        {/* Projects Sidebar (Enterprise mode only) */}
        {isEnterpriseMode && (
          <ProjectsSidebar
            sessionId={session.id}
            currentProjectId={session.project_id || null}
            onProjectSelect={handleProjectSelect}
            onNewProject={handleNewProject}
          />
        )}

        {/* Main Chat Area */}
        <div className="flex-1 min-w-0 overflow-hidden">
          <ChatContainer sessionId={session.id} />
        </div>
      </div>

      {/* Error notification */}
      {setupError && (
        <div className="fixed bottom-4 right-4 max-w-md p-4 bg-accent-red/10 border border-accent-red/30 rounded-lg">
          <p className="text-accent-red text-sm">{setupError}</p>
        </div>
      )}
    </div>
  );
}

export default App;
