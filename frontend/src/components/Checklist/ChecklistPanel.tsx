import { CheckCircle2, Circle, Zap, ListTodo } from 'lucide-react';

interface ChecklistPanelProps {
  content: string | null;
}

interface ParsedItem {
  icon: 'completed' | 'in_progress' | 'pending';
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

    // Check for status indicators
    if (trimmed.includes('[green]') || trimmed.includes('✓')) {
      items.push({
        icon: 'completed',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡]/g, '').trim(),
      });
    } else if (trimmed.includes('[yellow]') || trimmed.includes('⚡')) {
      items.push({
        icon: 'in_progress',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡]/g, '').trim(),
      });
    } else if (trimmed.includes('[dim]') || trimmed.includes('○')) {
      items.push({
        icon: 'pending',
        text: trimmed.replace(/\[.*?\]/g, '').replace(/[✓○⚡]/g, '').trim(),
      });
    }
  }

  return items;
}

export default function ChecklistPanel({ content }: ChecklistPanelProps) {
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
      case 'pending':
        return <Circle className="w-4 h-4 text-dark-text-muted" />;
    }
  };

  const completedCount = items.filter((i) => i.icon === 'completed').length;
  const totalCount = items.length;

  return (
    <div className="w-72 border-l border-dark-border bg-dark-surface flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <ListTodo className="w-5 h-5 text-accent-red" />
          <h2 className="font-semibold text-dark-text-primary">TODO</h2>
        </div>
        <div className="mt-1 text-sm text-dark-text-secondary">
          {completedCount} of {totalCount} completed
        </div>
        {/* Progress bar */}
        <div className="mt-2 h-1 bg-dark-border rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-red transition-all duration-300"
            style={{ width: `${(completedCount / totalCount) * 100}%` }}
          />
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto p-4">
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li
              key={index}
              className={`flex items-start gap-2 p-2 rounded ${
                item.icon === 'in_progress'
                  ? 'bg-status-running/10'
                  : item.icon === 'completed'
                  ? 'bg-status-done/5'
                  : ''
              }`}
            >
              <span className="flex-shrink-0 mt-0.5">{getIcon(item.icon)}</span>
              <span
                className={`text-sm ${
                  item.icon === 'completed'
                    ? 'text-dark-text-muted line-through'
                    : item.icon === 'in_progress'
                    ? 'text-dark-text-primary font-medium'
                    : 'text-dark-text-secondary'
                }`}
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
