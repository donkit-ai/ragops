// WebSocket protocol types

export type WebSocketMessageType =
  | 'stream_start'
  | 'content'
  | 'tool_call_start'
  | 'tool_call_end'
  | 'tool_call_error'
  | 'checklist_update'
  | 'stream_end'
  | 'stream_cancelled'
  | 'error'
  | 'pong'
  | 'spinner_start'
  | 'spinner_stop'
  | 'spinner_update'
  | 'progress_start'
  | 'progress_update'
  | 'progress_stop'
  | 'markdown'
  | 'success_message'
  | 'warning_message'
  | 'error_message'
  | 'info_message'
  | 'confirm_request'
  | 'choice_request';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  timestamp: number;
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  result_preview?: string;
  error?: string;
  code?: string;
  message?: string;
  current?: number;
  total?: number;
  // Interactive dialog fields
  request_id?: string;
  question?: string;
  default?: boolean;
  choices?: string[];
  title?: string;
  // Progress fields
  progress?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: 'running' | 'completed' | 'error';
  resultPreview?: string;
  error?: string;
}

export interface Session {
  id: string;
  provider: string;
  model: string | null;
  created_at: number;
  last_activity: number;
  is_connected: boolean;
  message_count: number;
  mcp_initialized: boolean;
  enterprise_mode?: boolean;
  project_id?: string;
}

export interface FileInfo {
  name: string;
  path: string;
  size: number;
  content_type?: string;
}
