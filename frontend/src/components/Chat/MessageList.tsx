import { useEffect, useRef } from 'react';
import { User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage, ContentPart } from '../../types/protocol';
import ToolCallCard from '../Tools/ToolCallCard';
import DonkitLogo from '../../assets/donkit-logo.svg';

interface MessageListProps {
  messages: ChatMessage[];
  leftPadding?: string;
  rightPadding?: string;
}

export default function MessageList({
  messages,
  leftPadding = 'var(--space-m)',
  rightPadding = 'var(--space-m)',
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--color-txt-icon-2)' }}>
        <div className="text-center">
          <img src={DonkitLogo} alt="Donkit" className="w-16 h-16 mx-auto" style={{ marginBottom: 'var(--space-m)', opacity: 0.3 }} />
          <p className="h3" style={{ marginBottom: 0 }}>Start a conversation</p>
          <p className="p2" style={{ marginTop: 'var(--space-s)' }}>Ask me to help build your RAG pipeline</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto min-h-0" style={{ 
      padding: 'var(--space-m)', 
      paddingLeft: leftPadding,
      paddingRight: rightPadding,
      backgroundColor: 'var(--color-bg)',
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-m)'
    }}>
      <div className="max-w-4xl mx-auto w-full flex flex-col" style={{ gap: 'var(--space-l)' }}>
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
          style={{ gap: 'var(--space-m)' }}
        >
          {/* Avatar */}
          <div
            className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center overflow-hidden ${
              message.role === 'user'
                ? 'bg-accent-blue text-white'
                : 'bg-transparent'
            }`}
          >
            {message.role === 'user' ? (
              <User className="w-5 h-5" />
            ) : (
              <img src={DonkitLogo} alt="Donkit" className="w-8 h-8" />
            )}
          </div>

          {/* Message content */}
          <div
            className="max-w-[75%]"
            style={{
              backgroundColor: message.role === 'user' ? 'var(--color-action-item-selected)' : 'transparent',
              color: message.role === 'user' ? 'var(--color-txt-icon-1)' : 'var(--color-txt-icon-1)',
              borderRadius: message.role === 'user' ? 'var(--space-l) var(--space-xs) var(--space-l) var(--space-l)' : 'var(--space-l) var(--space-l) var(--space-xs) var(--space-l)',
              padding: message.role === 'user' ? 'var(--space-xs) var(--space-l)' : '0',
              border: message.role === 'user' ? '1px solid var(--color-border)' : 'none'
            }}
          >
            {message.role === 'user' ? (
              <p className="whitespace-pre-wrap p1">{message.content}</p>
            ) : message.parts && message.parts.length > 0 ? (
              // Render parts in chronological order
              <div className="space-y-2" style={{ paddingTop: 0, marginTop: 0 }}>
                {message.parts.map((part: ContentPart, index: number) => (
                  <div key={index} style={index === 0 ? { marginTop: 0, paddingTop: 0 } : {}}>
                    {part.type === 'text' && part.content && (
                      <div className="prose max-w-none p1 agent-message" style={{ marginTop: 0, paddingTop: 0 }}>
                        <ReactMarkdown>{part.content}</ReactMarkdown>
                      </div>
                    )}
                    {part.type === 'tool' && part.toolCall && (
                      <ToolCallCard toolCall={part.toolCall} />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              // Fallback for messages without parts (backward compatibility)
              <>
                <div className="prose max-w-none p1 agent-message" style={{ marginTop: 0, paddingTop: 0 }}>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
                {message.toolCalls && message.toolCalls.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {message.toolCalls.map((toolCall) => (
                      <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Streaming indicator */}
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 bg-dark-text-secondary animate-pulse ml-1" />
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
      </div>
    </div>
  );
}
