import { useEffect, useRef } from 'react';
import { User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage, ContentPart } from '../../types/protocol';
import ToolCallCard from '../Tools/ToolCallCard';
import DonkitLogo from '../../assets/donkit-logo.svg';

interface MessageListProps {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-dark-text-secondary">
        <div className="text-center">
          <img src={DonkitLogo} alt="Donkit" className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg">Start a conversation</p>
          <p className="text-sm mt-2">Ask me to help build your RAG pipeline</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-dark-bg min-h-0">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
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
            className={`max-w-[75%] ${
              message.role === 'user'
                ? 'bg-accent-blue text-white rounded-2xl rounded-tr-sm px-4 py-2.5'
                : 'bg-dark-surface border border-dark-border rounded-2xl rounded-tl-sm px-4 py-2.5'
            }`}
          >
            {message.role === 'user' ? (
              <p className="whitespace-pre-wrap text-[15px]">{message.content}</p>
            ) : message.parts && message.parts.length > 0 ? (
              // Render parts in chronological order
              <div className="space-y-2">
                {message.parts.map((part: ContentPart, index: number) => (
                  <div key={index}>
                    {part.type === 'text' && part.content && (
                      <div className="prose prose-sm max-w-none">
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
                <div className="prose prose-sm max-w-none">
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
  );
}
