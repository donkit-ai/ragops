import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react';
import { Send, StopCircle, Loader2, Paperclip, X, File, ChevronDown, ChevronUp } from 'lucide-react';

interface MessageInputProps {
  onSend: (message: string) => void;
  onCancel: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  noCredits?: boolean;
  sessionId: string;
  onFilesUploaded: (files: Array<{ name: string; path: string; s3_path?: string }>, enterpriseMode: boolean) => void;
}

interface UploadedFile {
  name: string;
  path: string;
  size: number;
  s3_path?: string;
}

export default function MessageInput({
  onSend,
  onCancel,
  isStreaming,
  disabled,
  noCredits,
  sessionId,
  onFilesUploaded,
}: MessageInputProps) {
  const [input, setInput] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isFilesExpanded, setIsFilesExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Reset uploaded files when session changes
  useEffect(() => {
    setUploadedFiles([]);
    setError(null);
    setIsFilesExpanded(false);
  }, [sessionId]);

  const handleSubmit = () => {
    if (input.trim() && !isStreaming && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;

      setIsUploading(true);
      setError(null);

      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });

      try {
        const response = await fetch(`/api/v1/sessions/${sessionId}/files`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Upload failed');
        }

        const data = await response.json();
        const newFiles = data.uploaded.map((f: { name: string; path: string; size: number; s3_path?: string }) => ({
          name: f.name,
          path: f.path,
          size: f.size,
          s3_path: f.s3_path,
        }));

        setUploadedFiles((prev) => [...prev, ...newFiles]);
        onFilesUploaded(newFiles, data.enterprise_mode || false);

        if (data.errors && data.errors.length > 0) {
          setError(`Some files failed: ${data.errors.map((e: { name: string }) => e.name).join(', ')}`);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed');
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    },
    [sessionId, onFilesUploaded]
  );


  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !isStreaming) {
      setIsDragging(true);
    }
  }, [disabled, isStreaming]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled || isStreaming) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length === 0) return;

      setIsUploading(true);
      setError(null);

      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });

      try {
        const response = await fetch(`/api/v1/sessions/${sessionId}/files`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || 'Upload failed');
        }

        const data = await response.json();
        const newFiles = data.uploaded.map((f: { name: string; path: string; size: number; s3_path?: string }) => ({
          name: f.name,
          path: f.path,
          size: f.size,
          s3_path: f.s3_path,
        }));

        setUploadedFiles((prev) => [...prev, ...newFiles]);
        onFilesUploaded(newFiles, data.enterprise_mode || false);

        if (data.errors && data.errors.length > 0) {
          setError(`Some files failed: ${data.errors.map((e: { name: string }) => e.name).join(', ')}`);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed');
      } finally {
        setIsUploading(false);
      }
    },
    [sessionId, onFilesUploaded, disabled, isStreaming]
  );

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="px-6 py-4 bg-dark-bg">
      {/* Uploaded files list */}
      {uploadedFiles.length > 0 && (
        <div className="mb-3 max-w-4xl mx-auto">
          {uploadedFiles.length > 2 && (
            <button
              onClick={() => setIsFilesExpanded(!isFilesExpanded)}
              className="flex items-center gap-2 text-sm text-dark-text-secondary hover:text-dark-text-primary transition-colors mb-2"
            >
              {isFilesExpanded ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  <span>Hide files ({uploadedFiles.length})</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  <span>Show all files ({uploadedFiles.length})</span>
                </>
              )}
            </button>
          )}
          <div className="space-y-2">
            {(uploadedFiles.length <= 2 || isFilesExpanded
              ? uploadedFiles
              : uploadedFiles.slice(0, 2)
            ).map((file) => (
              <div
                key={file.path}
                className="flex items-center gap-2 bg-dark-surface border border-dark-border rounded-lg px-3 py-2 text-sm"
              >
                <File className="w-4 h-4 text-dark-text-muted flex-shrink-0" />
                <span className="flex-1 truncate text-dark-text-primary">{file.name}</span>
                <span className="text-dark-text-muted text-xs">{formatFileSize(file.size)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-3 max-w-4xl mx-auto text-sm text-accent-red flex items-center gap-1">
          <X className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Input field container - centered with max width */}
      <div
        className="max-w-4xl mx-auto"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div
          className={`flex flex-col gap-4 bg-dark-input border rounded-lg p-4 transition-all relative ${
            isDragging
              ? 'border-accent-red border-2 bg-accent-red/10 scale-[1.02]'
              : 'border-dark-border-input'
          }`}
        >
          {/* Drag overlay */}
          {isDragging && (
            <div className="absolute inset-0 flex items-center justify-center bg-accent-red/20 rounded-lg z-10 pointer-events-none">
              <div className="text-accent-red font-medium text-lg flex items-center gap-2">
                <Paperclip className="w-6 h-6" />
                Drop files here
              </div>
            </div>
          )}

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={noCredits ? 'You have run out of credits. Please top up your balance to continue.' : 'Provide a clear instruction for what your RAG pipeline should be able to do'}
            className="resize-none bg-transparent border-none text-dark-text-primary placeholder:text-dark-text-muted focus:outline-none disabled:opacity-50 text-[15px]"
            rows={1}
            disabled={disabled}
          />

          {/* Actions row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* Attach button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || disabled}
                className="flex items-center gap-2 px-2 py-1 text-sm text-dark-text-secondary hover:text-dark-text-primary transition-colors disabled:opacity-50"
                title="Attach files"
              >
                {isUploading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Paperclip className="w-4 h-4" />
                )}
                <span>Attach</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>

            {/* Send/Cancel button */}
            {isStreaming ? (
              <button
                onClick={onCancel}
                className="flex-shrink-0 w-10 h-10 bg-accent-red hover:bg-accent-red-hover text-white rounded-full flex items-center justify-center transition-colors"
                title="Stop generation"
              >
                <StopCircle className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || disabled}
                className="flex-shrink-0 w-10 h-10 bg-accent-red hover:bg-accent-red-hover disabled:bg-dark-border disabled:text-dark-text-muted text-white rounded-full flex items-center justify-center transition-colors"
                title="Send message"
              >
                {disabled ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
