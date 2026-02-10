import { useCallback, useEffect, useRef, useState } from 'react';
import { ChatMessage, ContentPart, ToolCall, WebSocketMessage } from '../../types/protocol';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useChecklist } from '../../hooks/useChecklist';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ChecklistPanel from '../Checklist/ChecklistPanel';
import ConnectionStatus from '../Layout/ConnectionStatus';
import { ConfirmDialog, ChoiceDialog } from '../Dialogs/InteractiveDialog';

interface InteractiveRequest {
  id: string;
  type: 'confirm' | 'choice';
  question?: string;
  title?: string;
  choices?: string[];
  defaultValue?: boolean;
}

interface ChatContainerProps {
  sessionId: string;
}

export default function ChatContainer({ sessionId }: ChatContainerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [interactiveRequests, setInteractiveRequests] = useState<InteractiveRequest[]>([]);
  const { checklist, updateFromMessage } = useChecklist(sessionId);
  const [isChecklistCollapsed, setIsChecklistCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const dialogsRef = useRef<HTMLDivElement>(null);

  // Track window size for mobile detection
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 800);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const generateId = () => Math.random().toString(36).substring(2, 9);

  // Load message history when session changes (e.g., switching projects)
  useEffect(() => {
    let mounted = true;

    const loadHistory = async () => {
      try {
        const response = await fetch(`/api/v1/sessions/${sessionId}/history`);
        if (!response.ok) {
          console.error('Failed to load history:', response.statusText);
          return;
        }

        const data = await response.json();
        const historyMessages: ChatMessage[] = [];

        // Convert history messages to ChatMessage format
        // Skip system messages, only show user and assistant
        for (const msg of data.messages || []) {
          if (msg.role === 'system') continue;

          historyMessages.push({
            id: generateId(),
            role: msg.role,
            content: msg.content || '',
            timestamp: Date.now() / 1000,
            isStreaming: false,
          });
        }

        if (mounted) {
          setMessages(historyMessages);
        }
      } catch (err) {
        console.error('Error loading history:', err);
      }
    };

    loadHistory();

    return () => {
      mounted = false;
    };
  }, [sessionId]);

  // Auto-scroll to dialogs when they appear
  useEffect(() => {
    if (interactiveRequests.length > 0 && dialogsRef.current) {
      console.log('[ChatContainer] Scrolling to dialogs');
      dialogsRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [interactiveRequests.length]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'stream_start':
        setIsStreaming(true);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: '',
            timestamp: message.timestamp,
            isStreaming: true,
            toolCalls: [],
            parts: [],
          },
        ]);
        break;

      case 'content':
        if (message.content) {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming) {
              // Update parts array for chronological display
              const parts = [...(last.parts || [])];
              const lastPart = parts[parts.length - 1];

              if (lastPart && lastPart.type === 'text') {
                // Append to existing text part
                parts[parts.length - 1] = {
                  ...lastPart,
                  content: (lastPart.content || '') + message.content,
                };
              } else {
                // Create new text part
                parts.push({ type: 'text', content: message.content });
              }

              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + message.content, parts },
              ];
            }
            return prev;
          });
        }
        break;

      case 'progress_update':
        // Update progress for the currently running tool
        if (message.progress !== undefined) {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming && last.toolCalls) {
              // Find the last running tool call and update its progress
              const updatedToolCalls = [...last.toolCalls];
              const runningIndex = updatedToolCalls.findIndex(tc => tc.status === 'running');
              const progressPreview = message.message ||
                `${message.progress}${message.total ? `/${message.total}` : ''}`;

              if (runningIndex !== -1) {
                updatedToolCalls[runningIndex] = {
                  ...updatedToolCalls[runningIndex],
                  resultPreview: progressPreview,
                };
              }

              // Also update in parts array
              const parts = last.parts?.map((part) =>
                part.type === 'tool' && part.toolCall?.status === 'running'
                  ? { ...part, toolCall: { ...part.toolCall, resultPreview: progressPreview } }
                  : part
              );

              return [
                ...prev.slice(0, -1),
                { ...last, toolCalls: updatedToolCalls, parts },
              ];
            }
            return prev;
          });
        }
        break;

      case 'tool_call_start':
        if (message.tool_name) {
          const toolCall: ToolCall = {
            id: generateId(),
            name: message.tool_name,
            args: message.tool_args || {},
            status: 'running',
          };
          setCurrentToolCalls((prev) => [...prev, toolCall]);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming) {
              // Add tool call to parts array for chronological display
              const parts: ContentPart[] = [...(last.parts || [])];
              parts.push({ type: 'tool', toolCall });

              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  toolCalls: [...(last.toolCalls || []), toolCall],
                  parts,
                },
              ];
            }
            return prev;
          });
        }
        break;

      case 'tool_call_end':
        if (message.tool_name) {
          setCurrentToolCalls((prev) =>
            prev.map((tc) =>
              tc.name === message.tool_name
                ? { ...tc, status: 'completed', resultPreview: message.result_preview }
                : tc
            )
          );
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming) {
              // Update tool call in both toolCalls and parts arrays
              const updateToolCall = (tc: ToolCall) =>
                tc.name === message.tool_name
                  ? { ...tc, status: 'completed' as const, resultPreview: message.result_preview }
                  : tc;

              const parts = last.parts?.map((part) =>
                part.type === 'tool' && part.toolCall && part.toolCall.name === message.tool_name
                  ? { ...part, toolCall: updateToolCall(part.toolCall) }
                  : part
              );

              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  toolCalls: last.toolCalls?.map(updateToolCall),
                  parts,
                },
              ];
            }
            return prev;
          });
        }
        break;

      case 'tool_call_error':
        if (message.tool_name) {
          setCurrentToolCalls((prev) =>
            prev.map((tc) =>
              tc.name === message.tool_name
                ? { ...tc, status: 'error', error: message.error }
                : tc
            )
          );
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === 'assistant' && last.isStreaming) {
              // Update tool call in both toolCalls and parts arrays
              const updateToolCall = (tc: ToolCall) =>
                tc.name === message.tool_name
                  ? { ...tc, status: 'error' as const, error: message.error }
                  : tc;

              const parts = last.parts?.map((part) =>
                part.type === 'tool' && part.toolCall && part.toolCall.name === message.tool_name
                  ? { ...part, toolCall: updateToolCall(part.toolCall) }
                  : part
              );

              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  toolCalls: last.toolCalls?.map(updateToolCall),
                  parts,
                },
              ];
            }
            return prev;
          });
        }
        break;

      case 'checklist_update':
        updateFromMessage(message.content || null);
        break;

      case 'stream_end':
      case 'stream_cancelled':
        setIsStreaming(false);
        setCurrentToolCalls([]);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant' && last.isStreaming) {
            return [...prev.slice(0, -1), { ...last, isStreaming: false }];
          }
          return prev;
        });
        break;

      case 'error':
        setIsStreaming(false);
        console.error('WebSocket error:', message.error);
        break;

      case 'confirm_request':
        console.log('[ChatContainer] Received confirm_request:', message);
        if (message.request_id) {
          console.log('[ChatContainer] Adding interactive request with id:', message.request_id);
          setInteractiveRequests((prev) => {
            const newRequests: InteractiveRequest[] = [
              ...prev,
              {
                id: message.request_id!,
                type: 'confirm' as const,
                question: message.question,
                defaultValue: message.default,
              },
            ];
            console.log('[ChatContainer] Interactive requests now:', newRequests);
            return newRequests;
          });
        }
        break;

      case 'choice_request':
        if (message.request_id) {
          setInteractiveRequests((prev) => [
            ...prev,
            {
              id: message.request_id!,
              type: 'choice' as const,
              title: message.title,
              choices: message.choices,
            },
          ]);
        }
        break;

      default:
        // Handle other message types if needed
        break;
    }
  }, [updateFromMessage]);

  const { status, sendChat, sendCancel, sendInteractiveResponse } = useWebSocket(sessionId, {
    onMessage: handleMessage,
  });

  const handleConfirmResponse = useCallback(
    (requestId: string, confirmed: boolean) => {
      console.log('[ChatContainer] handleConfirmResponse called:', { requestId, confirmed });
      sendInteractiveResponse(requestId, { confirmed });
      setInteractiveRequests((prev) => prev.filter((r) => r.id !== requestId));
    },
    [sendInteractiveResponse]
  );

  const handleChoiceResponse = useCallback(
    (requestId: string, choice: string) => {
      sendInteractiveResponse(requestId, { choice });
      setInteractiveRequests((prev) => prev.filter((r) => r.id !== requestId));
    },
    [sendInteractiveResponse]
  );

  const handleSend = useCallback(
    (content: string) => {
      console.log('[ChatContainer] handleSend called with:', content);
      console.log('[ChatContainer] WebSocket status:', status);
      const userMessage: ChatMessage = {
        id: generateId(),
        role: 'user',
        content,
        timestamp: Date.now() / 1000,
      };
      setMessages((prev) => [...prev, userMessage]);
      sendChat(content);
      console.log('[ChatContainer] sendChat called');
    },
    [sendChat, status]
  );

  const handleCancel = useCallback(() => {
    sendCancel();
  }, [sendCancel]);

  const handleFilesUploaded = useCallback((files: Array<{ name: string; path: string; s3_path?: string }>, enterpriseMode: boolean) => {
    // Build message with file paths for the agent
    const fileNames = files.map((f) => f.name);
    // In enterprise mode, use S3 paths; in local mode, use local paths
    const filePaths = files.map((f) => enterpriseMode && f.s3_path ? f.s3_path : f.path);

    let uploadMessage = '';
    if (fileNames.length === 1) {
      uploadMessage = `I've uploaded the file: ${fileNames[0]}.`;
    } else {
      uploadMessage = `I've uploaded ${fileNames.length} files: ${fileNames.join(', ')}.`;
    }

    // Add file paths so agent can use them
    uploadMessage += `\n\nFile locations:\n${filePaths.join('\n')}`;

    // Send to agent via WebSocket without showing in UI or persisting to history
    sendChat(uploadMessage, true);  // silent=true
  }, [sendChat]);

  // Calculate right padding for mobile when checklist is visible (mobile only)
  const collapsedChecklistWidth = '64px'; // w-16 = 4rem = 64px
  const mobileRightPadding = isMobile && checklist.hasChecklist
    ? `calc(var(--page-padding-hor) + ${collapsedChecklistWidth})`
    : 'var(--page-padding-hor)';
  
  // For MessageList, use space-m as base instead of page-padding-hor
  const mobileRightPaddingMessages = isMobile && checklist.hasChecklist
    ? `calc(var(--space-m) + ${collapsedChecklistWidth})`
    : 'var(--space-m)';

  return (
    <div className="flex h-full overflow-hidden" style={{ backgroundColor: 'var(--color-bg)' }}>
      {/* Main chat area - centered */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Header */}
        <div
          className="flex-shrink-0 flex items-center justify-between"
          style={{
            backgroundColor: 'var(--color-action-item-selected)',
            padding: `var(--space-xs) var(--page-padding-hor)`,
            paddingRight: mobileRightPadding,
          }}
        >
          <div className="flex items-center" style={{ gap: 'var(--space-m)' }}>
            <h1 className="h4" style={{ fontWeight: 500, margin: 0 }}>RAGOps Chat</h1>
            {interactiveRequests.length > 0 && (
              <span className="p2 inline-flex items-center" style={{ 
                padding: 'var(--space-xs) var(--space-s)', 
                borderRadius: '999px', 
                fontWeight: 500, 
                backgroundColor: 'var(--color-action-item-selected)', 
                color: 'var(--color-neutral)' 
              }}>
                ⚠️ Action Required
              </span>
            )}
          </div>
          <ConnectionStatus status={status} />
        </div>

        {/* Messages */}
        <MessageList messages={messages} rightPadding={mobileRightPaddingMessages} />

        {/* Interactive dialogs */}
        {interactiveRequests.length > 0 && (
          <>
            {console.log('[ChatContainer] Rendering interactive dialogs, count:', interactiveRequests.length)}
            <div
              ref={dialogsRef}
              className="flex-shrink-0"
              style={{
                padding: `var(--space-m) var(--page-padding-hor) 0`,
                paddingRight: mobileRightPadding,
                borderTop: '1px solid var(--color-border)',
                backgroundColor: 'var(--color-bg)',
              }}
            >
              <div className="max-w-4xl mx-auto w-full">
                <div
                  className="p2"
                  style={{ marginBottom: 'var(--space-s)', fontWeight: 500, color: 'var(--color-neutral)' }}
                >
                  ⚠️ Action Required ({interactiveRequests.length})
                </div>
                {interactiveRequests.map((request) =>
                  request.type === 'confirm' ? (
                    <ConfirmDialog
                      key={request.id}
                      requestId={request.id}
                      question={request.question || 'Continue?'}
                      defaultValue={request.defaultValue ?? true}
                      onResponse={handleConfirmResponse}
                    />
                  ) : (
                    <ChoiceDialog
                      key={request.id}
                      requestId={request.id}
                      title={request.title || 'Select an option'}
                      choices={request.choices || []}
                      onResponse={handleChoiceResponse}
                    />
                  )
                )}
              </div>
            </div>
          </>
        )}

        {/* Input with file upload */}
        <div className="flex-shrink-0">
          <MessageInput
            onSend={handleSend}
            onCancel={handleCancel}
            isStreaming={isStreaming}
            disabled={status !== 'connected'}
            sessionId={sessionId}
            onFilesUploaded={handleFilesUploaded}
            rightPadding={mobileRightPadding}
          />
        </div>
      </div>

      {/* Right sidebar - only show when there's content */}
      {checklist.hasChecklist && (
        <div 
          className="flex-shrink-0 overflow-auto checklist-panel-mobile" 
          style={{ 
            borderLeft: '1px solid var(--color-border)'
          }}
        >
          <ChecklistPanel 
            content={checklist.content} 
            onCollapseChange={setIsChecklistCollapsed}
          />
        </div>
      )}
    </div>
  );
}
