import { useState } from 'react';
import { useProjects } from '../../hooks/useProjects';
import { MessageSquare, RefreshCw, Loader2, Plus, AlertCircle, Folder } from 'lucide-react';
import FolderGitIcon from '../../assets/icons/folder-git.svg';
import ArrowRightToLineIcon from '../../assets/icons/arrow-right-to-line.svg';
import ArrowLeftToLineIcon from '../../assets/icons/arrow-left-to-line.svg';

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
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isHoveringHeader, setIsHoveringHeader] = useState(false);
  const [isHoveringCollapseButton, setIsHoveringCollapseButton] = useState(false);

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

  const handleCollapse = (collapsed: boolean) => {
    setIsCollapsed(collapsed);
  };

  if (isCollapsed) {
    return (
      <div
        className="w-16 flex flex-col items-center h-full"
        style={{
          backgroundColor: 'var(--color-bg)',
          borderRight: '1px solid var(--color-border)',
        }}
      >
        {/* Header - collapsed (mirrors ChecklistPanel) */}
        <div
          className="flex flex-col items-center cursor-pointer relative"
          style={{
            padding: 'var(--space-s) 0 var(--space-m)',
            borderBottom: '1px solid var(--color-border)',
            width: '100%',
            backgroundColor: isHoveringHeader ? 'var(--color-action-item-hover)' : 'transparent',
            transition: 'background-color 0.2s ease',
          }}
          title="Expand projects"
          onClick={() => handleCollapse(false)}
          onMouseEnter={() => setIsHoveringHeader(true)}
          onMouseLeave={() => setIsHoveringHeader(false)}
        >
          <div className="relative flex items-center justify-center" style={{ height: '24px' }}>
            <img
              src={FolderGitIcon}
              alt="Projects"
              className="w-6 h-6 block icon-txt2 transition-opacity"
              style={{
                opacity: isHoveringHeader ? 0 : 0.6,
                transition: 'opacity 0.2s ease',
              }}
            />
            <img
              src={ArrowRightToLineIcon}
              alt="Expand"
              className="w-6 h-6 block icon-txt2 transition-opacity"
              style={{
                position: 'absolute',
                opacity: isHoveringHeader ? 1 : 0,
                transition: 'opacity 0.2s ease',
                left: '50%',
                transform: 'translateX(-50%)',
              }}
            />
          </div>
          <div
            className="p2"
            style={{
              marginTop: 'var(--space-xs)',
              textAlign: 'center',
              fontSize: '10px',
              fontWeight: 500,
              color: 'var(--color-txt-icon-2)',
            }}
          >
            {projects.length}
          </div>
        </div>

        {/* New project icon button */}
        <div
          className="flex-1"
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            paddingTop: 'var(--space-s)',
          }}
        >
          <button
            onClick={onNewProject}
            title="New project"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '999px',
              border: '1px solid var(--color-border)',
              backgroundColor: 'transparent',
              color: 'var(--color-txt-icon-2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease',
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.backgroundColor = 'var(--color-action-item-hover)';
              el.style.borderColor = 'var(--color-border-hover)';
              el.style.color = 'var(--color-txt-icon-1)';
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.backgroundColor = 'transparent';
              el.style.borderColor = 'var(--color-border)';
              el.style.color = 'var(--color-txt-icon-2)';
            }}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="w-80 flex flex-col h-full"
      style={{
        backgroundColor: 'var(--color-bg)',
        borderRight: '1px solid var(--color-border)',
      }}
    >
      {/* Header */}
      <div
        className="flex-shrink-0"
        style={{
          padding: 'var(--space-s) var(--space-m) var(--space-m)',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <div
          className="flex items-center justify-between"
          style={{ marginBottom: 'var(--space-m)' }}
        >
          <div className="flex items-center" style={{ gap: 'var(--space-xs)' }}>
            <h2
              className="p1 flex items-center"
              style={{ fontWeight: 500, gap: 'var(--space-s)' }}
            >
              <img src={FolderGitIcon} alt="" className="w-6 h-6 block icon-txt1" />
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
          <button
            onClick={() => handleCollapse(true)}
            className="cursor-pointer"
            style={{
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none',
            }}
            onMouseEnter={() => setIsHoveringCollapseButton(true)}
            onMouseLeave={() => setIsHoveringCollapseButton(false)}
            title="Collapse projects"
          >
            <img
              src={ArrowLeftToLineIcon}
              alt="Collapse"
              className={`w-5 h-5 ${isHoveringCollapseButton ? 'icon-txt1' : 'icon-txt2'}`}
              style={{
                transition: 'filter 0.2s ease, opacity 0.2s ease',
              }}
            />
          </button>
        </div>

        {/* New Project Button */}
        <button
          onClick={onNewProject}
          className="btn-secondary w-full justify-center"
          style={{ paddingTop: 'var(--space-xs)', paddingBottom: 'var(--space-xs)' }}
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto" style={{ padding: 'var(--space-m)' }}>
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
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-xs)',
            }}
          >
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => onProjectSelect(project.id)}
                style={{
                  width: '100%',
                  padding: 'var(--space-xs) var(--space-s)',
                  textAlign: 'left',
                  borderRadius: 'var(--space-xs)',
                  backgroundColor:
                    currentProjectId === project.id
                      ? 'var(--color-action-item-selected)'
                      : 'transparent',
                  border: '1px solid var(--color-border)',
                  transition: 'background-color 0.2s ease, border-color 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.backgroundColor = 'var(--color-action-item-hover)';
                  el.style.borderColor = 'var(--color-border-hover)';
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.backgroundColor =
                    currentProjectId === project.id
                      ? 'var(--color-action-item-selected)'
                      : 'transparent';
                  el.style.borderColor = 'var(--color-border)';
                }}
              >
                <div className="flex-1 min-w-0">
                  <div className="p2 truncate" style={{ fontWeight: 500 }}>{getProjectTitle(project)}</div>
                  <div className="flex items-center" style={{ gap: 'var(--space-s)', marginTop: 'var(--space-xs)', fontSize: 'var(--font-size-p2)', color: 'var(--color-txt-icon-2)' }}>
                    <span className="flex items-center" style={{ gap: 'var(--space-xs)' }}>
                      <MessageSquare className="w-3 h-3" />
                      <span>{project.message_count} messages</span>
                    </span>
                    <span className="inline-flex items-center">•</span>
                    <span className="inline-flex items-center">{formatDate(project.updated_at || project.created_at)}</span>
                    {currentProjectId === project.id && (
                      <span className="inline-flex items-center self-center" style={{ marginLeft: 'auto' }}>
                        <span className="flex-shrink-0 w-2 h-2 bg-accent-green rounded-full" />
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
