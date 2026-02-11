import { useState } from 'react';
import { CheckCircle2, Circle, Zap, ListTodo, XCircle } from 'lucide-react';
import ArrowRightToLineIcon from '../../assets/icons/arrow-right-to-line.svg';
import ArrowLeftToLineIcon from '../../assets/icons/arrow-left-to-line.svg';

interface ChecklistPanelProps {
  content: string | null;
  onCollapseChange?: (isCollapsed: boolean) => void;
}

interface ParsedItem {
  icon: 'completed' | 'in_progress' | 'pending' | 'failed';
  text: string;
}

function parseChecklistContent(content: string): ParsedItem[] {
  // Parse the Rich-formatted checklist content
  // Format: "  [icon] text"
  const lines = content.split('\n');
  const items: ParsedItem[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('[white on blue]') || trimmed === '') {
      continue;
    }

    // Check for status indicators (failed first so [red] wins over [green] in same line)
    if (trimmed.includes('[red]') || trimmed.includes('✗') || trimmed.includes('\u2717') || trimmed.includes('[/red]')) {
      items.push({
        icon: 'failed',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡✗\u2717]/g, '').trim(),
      });
    } else if (trimmed.includes('[green]') || trimmed.includes('✓')) {
      items.push({
        icon: 'completed',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡✗\u2717]/g, '').trim(),
      });
    } else if (trimmed.includes('[yellow]') || trimmed.includes('⚡')) {
      items.push({
        icon: 'in_progress',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡✗\u2717]/g, '').trim(),
      });
    } else if (trimmed.includes('[dim]') || trimmed.includes('○')) {
      items.push({
        icon: 'pending',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡✗\u2717]/g, '').trim(),
      });
    }
  }

  return items;
}

export default function ChecklistPanel({ content, onCollapseChange }: ChecklistPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isHoveringHeader, setIsHoveringHeader] = useState(false);
  const [isHoveringCollapseButton, setIsHoveringCollapseButton] = useState(false);

  const handleCollapse = (collapsed: boolean) => {
    setIsCollapsed(collapsed);
    onCollapseChange?.(collapsed);
  };

  if (!content) {
    return null;
  }

  const items = parseChecklistContent(content);

  const getIcon = (type: ParsedItem['icon']) => {
    switch (type) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-status-done" />;
      case 'in_progress':
        return <Zap className="w-4 h-4 text-status-running animate-pulse" />;
      case 'failed':
        return <XCircle className="w-4 h-4" style={{ color: 'var(--color-error)' }} />;
      case 'pending':
        return <Circle className="w-4 h-4 text-dark-text-muted" />;
    }
  };

  const completedCount = items.filter((i) => i.icon === 'completed').length;
  const totalCount = items.length;
  const currentStepIndex = items.findIndex((i) => i.icon === 'in_progress');
  // If no step is in progress, current step is the next one after completed steps
  const currentStepNumber = currentStepIndex !== -1 ? currentStepIndex + 1 : Math.min(completedCount + 1, totalCount);

  if (isCollapsed) {
    return (
      <div className="w-16 flex flex-col items-center" style={{ 
        backgroundColor: 'var(--color-bg)',
        borderLeft: '1px solid var(--color-border)'
      }}>
        {/* Header - collapsed */}
        <div 
          className="flex flex-col items-center cursor-pointer relative"
          style={{ 
            padding: 'var(--space-m)', 
            borderBottom: '1px solid var(--color-border)',
            width: '100%',
            backgroundColor: isHoveringHeader ? 'var(--color-action-item-hover)' : 'transparent',
            transition: 'background-color 0.2s ease'
          }}
          onClick={() => handleCollapse(false)}
          onMouseEnter={() => setIsHoveringHeader(true)}
          onMouseLeave={() => setIsHoveringHeader(false)}
        >
          <div className="relative flex items-center justify-center" style={{ width: '100%' }}>
            <ListTodo 
              className="w-5 h-5 transition-opacity" 
              style={{ 
                color: 'var(--color-txt-icon-2)',
                opacity: isHoveringHeader ? 0 : 1,
                transition: 'opacity 0.2s ease'
              }} 
            />
            <img 
              src={ArrowLeftToLineIcon} 
              alt="Expand" 
              className="w-5 h-5 icon-txt2 transition-opacity"
              style={{ 
                position: 'absolute',
                opacity: isHoveringHeader ? 1 : 0,
                transition: 'opacity 0.2s ease',
                left: '50%',
                transform: 'translateX(-50%)'
              }}
            />
          </div>
          <div className="p2" style={{ 
            marginTop: 'var(--space-xs)', 
            textAlign: 'center',
            fontSize: '10px',
            fontWeight: 500,
            color: 'var(--color-txt-icon-2)'
          }}>
            {currentStepNumber}/{totalCount}
          </div>
        </div>

        {/* Items - vertical icons (no connecting lines in collapsed view) */}
        <div className="flex-1 overflow-y-auto" style={{ 
          paddingTop: 'var(--space-s)',
          paddingBottom: 'var(--space-s)',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 0
        }}>
          {items.map((item, index) => (
            <div
              key={index}
              className="flex flex-col items-center"
              style={{
                paddingTop: 'var(--space-s)',
                paddingBottom: 'var(--space-s)',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title={item.text}
            >
              <div style={{ position: 'relative', zIndex: 1 }}>
                {getIcon(item.icon)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="w-72 flex flex-col">
      {/* Header */}
      <div style={{ padding: 'var(--space-m)', borderBottom: '1px solid var(--color-border)' }}>
        <div className="flex items-center justify-between" style={{ gap: 'var(--space-s)' }}>
          <div className="flex items-center" style={{ gap: 'var(--space-s)' }}>
            <ListTodo className="w-5 h-5" style={{ color: 'var(--color-txt-icon-1)' }} />
            <h2 className="h4" style={{ fontWeight: 500 }}>TODO</h2>
          </div>
          <button
            onClick={() => handleCollapse(true)}
            className="cursor-pointer"
            style={{
              padding: 'var(--space-xs)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'transparent',
              border: 'none'
            }}
            onMouseEnter={() => setIsHoveringCollapseButton(true)}
            onMouseLeave={() => setIsHoveringCollapseButton(false)}
            title="Collapse checklist"
          >
            <img 
              src={ArrowRightToLineIcon} 
              alt="Collapse" 
              className={`w-5 h-5 ${isHoveringCollapseButton ? 'icon-txt1' : 'icon-txt2'}`}
              style={{
                transition: 'filter 0.2s ease, opacity 0.2s ease'
              }}
            />
          </button>
        </div>
        <div className="p2" style={{ marginTop: 'var(--space-xs)' }}>
          {completedCount} of {totalCount} completed
        </div>
        {/* Progress bar */}
        <div style={{ 
          marginTop: 'var(--space-s)', 
          height: '4px', 
          backgroundColor: 'var(--color-border)', 
          borderRadius: '999px', 
          overflow: 'hidden' 
        }}>
          <div
            style={{ 
              height: '100%', 
              backgroundColor: 'var(--color-accent)', 
              transition: 'width 0.3s ease',
              width: `${(completedCount / totalCount) * 100}%` 
            }}
          />
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto" style={{ padding: 'var(--space-m)' }}>
        <ul style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-s)' }}>
          {items.map((item, index) => (
            <li
              key={index}
              className="flex items-start rounded"
              style={{
                gap: 'var(--space-s)',
                padding: 'var(--space-s)',
                backgroundColor:
                  item.icon === 'in_progress'
                    ? 'var(--color-action-item-selected)'
                    : item.icon === 'completed'
                      ? 'var(--color-action-item-hover)'
                      : item.icon === 'failed'
                        ? 'rgba(255, 18, 0, 0.1)'
                        : 'transparent'
              }}
            >
              <span className="flex-shrink-0" style={{ marginTop: '2px' }}>{getIcon(item.icon)}</span>
              <span
                className="p2"
                style={{
                  color: item.icon === 'completed' ? 'var(--color-txt-icon-2)' : item.icon === 'in_progress' ? 'var(--color-txt-icon-1)' : item.icon === 'failed' ? 'var(--color-error)' : 'var(--color-txt-icon-2)',
                  textDecoration: item.icon === 'completed' ? 'line-through' : 'none',
                  fontWeight: item.icon === 'in_progress' ? 500 : item.icon === 'failed' ? 500 : 300
                }}
              >
                {item.text}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
