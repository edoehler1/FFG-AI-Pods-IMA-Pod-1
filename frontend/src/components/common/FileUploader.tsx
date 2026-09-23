import { useCallback, useState } from 'react';

interface FileUploaderProps {
  label: string;
  description: string;
  accept: string;
  onUpload: (file: File) => Promise<unknown>;
}

export default function FileUploader({ label, description, accept, onUpload }: FileUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setUploading(true);
    setResult(null);
    setError(null);

    try {
      const res = await onUpload(file);
      setResult(res as Record<string, unknown>);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      setError(msg);
    } finally {
      setUploading(false);
    }
  }, [onUpload]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      <h3 className="text-sm font-semibold text-slate-900 mb-1">{label}</h3>
      <p className="text-xs text-slate-500 mb-4">{description}</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300'
        }`}
      >
        {uploading ? (
          <p className="text-sm text-slate-600">Uploading...</p>
        ) : (
          <>
            <p className="text-sm text-slate-600 mb-2">Drag and drop a file here, or</p>
            <label className="cursor-pointer inline-block px-4 py-2 bg-slate-800 text-white text-sm rounded hover:bg-slate-700 transition-colors">
              Browse files
              <input type="file" accept={accept} onChange={handleChange} className="hidden" />
            </label>
            <p className="text-xs text-slate-400 mt-2">Accepts {accept}</p>
          </>
        )}
      </div>

      {result && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
          {Object.entries(result).map(([key, val]) => (
            <div key={key}><span className="font-medium">{key.replace(/_/g, ' ')}:</span> {String(val)}</div>
          ))}
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
          {error}
        </div>
      )}
    </div>
  );
}
