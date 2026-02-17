import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react';
import { Send, StopCircle, Loader2, Paperclip, X, File, ChevronDown } from 'lucide-react';

interface MessageInputProps {
  onSend: (message: string) => void;
  onCancel: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  sessionId: string;
  onFilesUploaded: (files: Array<{ name: string; path: string; s3_path?: string }>, enterpriseMode: boolean) => void;
  leftPadding?: string;
  rightPadding?: string;
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
  sessionId,
  onFilesUploaded,
  leftPadding = 'var(--page-padding-hor)',
  rightPadding = 'var(--page-padding-hor)',
}: MessageInputProps) {
  const [input, setInput] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [areFilesExpanded, setAreFilesExpanded] = useState(true);
  const [isHoveringFilesHeader, setIsHoveringFilesHeader] = useState(false);

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
    setAreFilesExpanded(true);
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
    <div style={{ 
      padding: `var(--space-m) var(--page-padding-hor)`, 
      paddingLeft: leftPadding,
      paddingRight: rightPadding,
      backgroundColor: 'var(--color-bg)' 
    }}>
      {/* Uploaded files list */}
      {uploadedFiles.length > 0 && (
        <div
          className="max-w-4xl mx-auto"
          style={{
            marginBottom: 'var(--space-m)',
          }}
        >
          {/* Shared container for all files (including header/chevron) */}
          <div
            style={{
              backgroundColor: 'var(--color-bg)',
              border: `1px solid ${
                uploadedFiles.length > 2 &&
                !areFilesExpanded &&
                isHoveringFilesHeader
                  ? 'var(--color-border-hover)'
                  : 'var(--color-border)'
              }`,
              borderRadius: 'var(--space-s)',
              padding: 'var(--space-s) var(--space-m)',
              transition: 'border-color 0.15s ease',
            }}
          >
            {uploadedFiles.length > 2 && (
              <button
                type="button"
                onClick={() => setAreFilesExpanded((prev) => !prev)}
                className="w-full flex items-center justify-between"
                style={{
                  marginBottom: areFilesExpanded ? 'var(--space-xs)' : 0,
                  padding: 0,
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                }}
                onMouseEnter={() => setIsHoveringFilesHeader(true)}
                onMouseLeave={() => setIsHoveringFilesHeader(false)}
              >
                <span
                  className="p1"
                  style={{
                    fontWeight: 500,
                    color: 'var(--color-txt-icon-2)',
                  }}
                >
                  {uploadedFiles.length} files
                </span>
                <ChevronDown
                  style={{
                    width: 24,
                    height: 24,
                    color: isHoveringFilesHeader
                      ? 'var(--color-txt-icon-1)'
                      : 'var(--color-txt-icon-2)',
                    transform: areFilesExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.15s ease, color 0.15s ease',
                  }}
                />
              </button>
            )}

            {((uploadedFiles.length <= 2) || areFilesExpanded) && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-xs)',
                  fontSize: 'var(--font-size-p2)',
                }}
              >
                {uploadedFiles.map((file) => (
                  <div
                    key={file.path}
                    className="flex items-center"
                    style={{
                      gap: 'var(--space-s)',
                    }}
                  >
                    <File className="w-4 h-4 text-dark-text-muted flex-shrink-0" />
                    <span className="flex-1 truncate text-dark-text-primary">{file.name}</span>
                    <span className="text-dark-text-muted text-xs">{formatFileSize(file.size)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="max-w-4xl mx-auto flex items-center" style={{ 
          marginBottom: 'var(--space-m)', 
          fontSize: 'var(--font-size-p2)', 
          color: 'var(--color-accent)',
          gap: 'var(--space-xs)'
        }}>
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
          className="flex flex-col transition-all relative"
          style={{
            gap: 'var(--space-m)',
            backgroundColor: 'transparent',
            border: isDragging ? '2px solid var(--color-success)' : '1px solid var(--color-border)',
            borderRadius: 'var(--space-s)',
            padding: 'var(--space-m)',
            transform: isDragging ? 'scale(1.02)' : 'scale(1)',
            transition: 'border-color 0.2s ease'
          }}
          onMouseEnter={(e) => {
            if (!isDragging) {
              e.currentTarget.style.borderColor = 'var(--color-border-hover)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isDragging) {
              e.currentTarget.style.borderColor = 'var(--color-border)';
            }
          }}
        >
          {/* Drag overlay */}
          {isDragging && (
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none" style={{ 
              backgroundColor: 'var(--color-action-item-selected)', 
              borderRadius: 'var(--space-s)' 
            }}>
              <div className="font-medium flex items-center" style={{ 
                color: 'var(--color-success)', 
                fontSize: 'var(--font-size-h3)',
                gap: 'var(--space-s)'
              }}>
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
            placeholder="Provide a clear instruction for what your RAG pipeline should be able to do"
            style={{
              resize: 'none',
              backgroundColor: 'transparent',
              border: 'none',
              color: 'var(--color-txt-icon-1)',
              fontSize: 'var(--font-size-p1)',
              fontFamily: 'inherit',
              outline: 'none'
            }}
            className="disabled:opacity-50"
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
                className="flex items-center transition-colors disabled:opacity-50"
                style={{ 
                  gap: 'var(--space-s)', 
                  padding: 'var(--space-xs) var(--space-s)', 
                  fontSize: 'var(--font-size-p2)', 
                  color: 'var(--color-txt-icon-2)'
                }}
                onMouseEnter={(e) => {
                  if (!isUploading && !disabled) {
                    e.currentTarget.style.color = 'var(--color-txt-icon-1)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--color-txt-icon-2)';
                }}
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
                className="flex-shrink-0 flex items-center justify-center transition-colors"
                style={{
                  width: '40px',
                  height: '40px',
                  backgroundColor: 'var(--color-accent)',
                  borderRadius: '50%',
                  color: 'var(--color-white)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-accent)';
                }}
                title="Stop generation"
              >
                <StopCircle className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || disabled}
                className="flex-shrink-0 flex items-center justify-center transition-colors"
                style={{
                  width: '40px',
                  height: '40px',
                  backgroundColor: (!input.trim() || disabled) ? 'var(--color-border)' : 'var(--color-accent)',
                  borderRadius: '50%',
                  color: (!input.trim() || disabled) ? 'var(--color-txt-icon-2)' : 'var(--color-white)'
                }}
                onMouseEnter={(e) => {
                  if (input.trim() && !disabled) {
                    e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = (!input.trim() || disabled) ? 'var(--color-border)' : 'var(--color-accent)';
                }}
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
