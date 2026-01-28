import { useCallback, useState } from 'react';
import { Upload, X, File, Loader2 } from 'lucide-react';

interface FileUploadProps {
  sessionId: string;
  onFilesUploaded: (files: Array<{ name: string; path: string; s3_path?: string }>, enterpriseMode: boolean) => void;
}

interface UploadedFile {
  name: string;
  path: string;
  size: number;
  s3_path?: string;
}

export default function FileUpload({ sessionId, onFilesUploaded }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length === 0) return;

      await uploadFiles(files);
    },
    [sessionId]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;

      await uploadFiles(files);
      e.target.value = ''; // Reset input
    },
    [sessionId]
  );

  const uploadFiles = async (files: File[]) => {
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
  };


  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="border-t border-dark-border bg-dark-surface px-4 py-2">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-3 text-center transition-colors ${
          isDragging
            ? 'border-accent-red bg-accent-red/10'
            : 'border-dark-border hover:border-dark-text-muted'
        }`}
      >
        {isUploading ? (
          <div className="flex items-center justify-center gap-2 text-dark-text-secondary">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Uploading...</span>
          </div>
        ) : (
          <label className="cursor-pointer flex items-center justify-center gap-2 text-dark-text-secondary hover:text-dark-text-primary transition-colors">
            <Upload className="w-5 h-5" />
            <span>Drag files here or click to upload</span>
            <input
              type="file"
              multiple
              className="hidden"
              onChange={handleFileSelect}
            />
          </label>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-2 text-sm text-accent-red flex items-center gap-1">
          <X className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Uploaded files list */}
      {uploadedFiles.length > 0 && (
        <div className="mt-2 space-y-1">
          {uploadedFiles.map((file) => (
            <div
              key={file.path}
              className="flex items-center gap-2 bg-dark-bg border border-dark-border rounded px-2 py-1.5 text-sm"
            >
              <File className="w-4 h-4 text-dark-text-muted" />
              <span className="flex-1 truncate text-dark-text-primary">{file.name}</span>
              <span className="text-dark-text-muted text-xs">{formatFileSize(file.size)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
