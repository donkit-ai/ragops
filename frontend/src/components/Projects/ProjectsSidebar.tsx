import { useProjects } from '../../hooks/useProjects';
import { MessageSquare, RefreshCw, Loader2, Plus, AlertCircle, Folder } from 'lucide-react';
import FilesIcon from '../../assets/icons/files.svg';

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
    <div className="w-80 flex flex-col h-full" style={{ 
      backgroundColor: 'var(--color-action-item-selected)', 
      borderRight: '1px solid var(--color-border)' 
    }}>
      {/* Header */}
      <div className="flex-shrink-0" style={{ 
        padding: 'var(--space-m)', 
        borderBottom: '1px solid var(--color-border)' 
      }}>
        <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-m)' }}>
          <h2 className="h3 flex items-center" style={{ fontWeight: 500, gap: 'var(--space-s)' }}>
            <img
              src={FilesIcon}
              alt=""
              className="icon-txt1"
              style={{
                width: '20px',
                height: '20px',
              }}
            />
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
          className="btn-primary w-full justify-center"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto">
        {loading && projects.length === 0 ? (
          <div className="flex items-center justify-center" style={{ height: '128px', color: 'var(--color-txt-icon-2)' }}>
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : error ? (
          <div style={{ padding: 'var(--space-m)', textAlign: 'center' }}>
            <AlertCircle className="w-8 h-8 mx-auto" style={{ color: 'var(--color-accent)', marginBottom: 'var(--space-s)' }} />
            <p className="p2">{error}</p>
            <button
              onClick={refreshProjects}
              className="p2"
              style={{ marginTop: 'var(--space-s)', color: 'var(--color-accent)' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.textDecoration = 'underline';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.textDecoration = 'none';
              }}
            >
              Try again
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div style={{ padding: 'var(--space-m)', textAlign: 'center', color: 'var(--color-txt-icon-2)' }}>
            <Folder className="w-12 h-12 mx-auto" style={{ marginBottom: 'var(--space-s)', opacity: 0.3 }} />
            <p className="p2">No projects yet</p>
            <p className="p2" style={{ marginTop: 'var(--space-xs)', fontSize: 'var(--font-size-p2)' }}>Create your first project to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-dark-border">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => onProjectSelect(project.id)}
                style={{
                  width: '100%',
                  padding: 'var(--space-m)',
                  textAlign: 'left',
                  backgroundColor: currentProjectId === project.id ? 'var(--color-bg)' : 'transparent',
                  borderLeft: currentProjectId === project.id ? `4px solid var(--color-accent)` : 'none',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-action-item-hover)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = currentProjectId === project.id ? 'var(--color-bg)' : 'transparent';
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="p2 truncate" style={{ fontWeight: 500 }}>{getProjectTitle(project)}</div>
                    <div className="flex items-center" style={{ gap: 'var(--space-s)', marginTop: 'var(--space-xs)', fontSize: 'var(--font-size-p2)', color: 'var(--color-txt-icon-2)' }}>
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
