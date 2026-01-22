import { useProjects } from '../../hooks/useProjects';
import { Folder, MessageSquare, RefreshCw, Loader2, Plus, AlertCircle } from 'lucide-react';

interface ProjectsSidebarProps {
  sessionId: string;
  currentProjectId: string | null;
  onProjectSelect: (projectId: string) => void;
  onNewProject: () => void;
}

export default function ProjectsSidebar({
  sessionId,
  currentProjectId,
  onProjectSelect,
  onNewProject,
}: ProjectsSidebarProps) {
  const { projects, loading, error, refreshProjects } = useProjects(sessionId);

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getProjectTitle = (project: { id: string; rag_use_case?: string }) => {
    if (project.rag_use_case) {
      return project.rag_use_case;
    }
    return `Project ${project.id.slice(0, 8)}`;
  };

  return (
    <div className="w-80 bg-dark-surface border-r border-dark-border flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-dark-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-dark-text-primary flex items-center gap-2">
            <Folder className="w-5 h-5" />
            Projects
          </h2>
          <button
            onClick={refreshProjects}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-dark-bg transition-colors text-dark-text-muted hover:text-dark-text-primary disabled:opacity-50"
            title="Refresh projects"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* New Project Button */}
        <button
          onClick={onNewProject}
          className="w-full py-2 px-3 rounded-lg bg-accent-red hover:bg-accent-red-hover text-white font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto">
        {loading && projects.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-dark-text-muted">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : error ? (
          <div className="p-4 text-center">
            <AlertCircle className="w-8 h-8 text-accent-red mx-auto mb-2" />
            <p className="text-sm text-dark-text-muted">{error}</p>
            <button
              onClick={refreshProjects}
              className="mt-2 text-sm text-accent-red hover:underline"
            >
              Try again
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div className="p-4 text-center text-dark-text-muted">
            <Folder className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No projects yet</p>
            <p className="text-xs mt-1">Create your first project to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-dark-border">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => onProjectSelect(project.id)}
                className={`
                  w-full p-3 text-left hover:bg-dark-bg transition-colors
                  ${
                    currentProjectId === project.id
                      ? 'bg-dark-bg border-l-4 border-accent-red'
                      : ''
                  }
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-dark-text-primary truncate">
                      {getProjectTitle(project)}
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-dark-text-muted">
                      <MessageSquare className="w-3 h-3" />
                      <span>{project.message_count} messages</span>
                      <span>•</span>
                      <span>{formatDate(project.updated_at || project.created_at)}</span>
                    </div>
                  </div>
                  {currentProjectId === project.id && (
                    <div className="flex-shrink-0 w-2 h-2 bg-accent-green rounded-full ml-2" />
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
