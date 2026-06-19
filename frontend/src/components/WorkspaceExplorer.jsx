import { useState, useEffect, useCallback } from 'react';

function formatBytes(bytes, decimals = 2) {
  if (!bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default function WorkspaceExplorer({ sessionToken, onToast, filterType = 'all' }) {
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchFiles = useCallback(async () => {
    if (!sessionToken) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/workspace/files', {
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setFiles(data);
      } else {
        console.error("Failed to fetch workspace files");
      }
    } catch (err) {
      console.error("Error fetching workspace files:", err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionToken]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Expose reload mechanism globally or via window for upload updates
  useEffect(() => {
    window.reloadWorkspaceFiles = fetchFiles;
    return () => {
      delete window.reloadWorkspaceFiles;
    };
  }, [fetchFiles]);

  const handleDelete = async (filename) => {
    const confirmed = window.confirm(`Are you sure you want to delete '${filename}'? This will also remove it from search indexing.`);
    if (!confirmed) return;

    try {
      const res = await fetch(`/api/workspace/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        }
      });
      if (res.ok) {
        if (onToast) {
          onToast({
            title: "File Deleted",
            message: `'${filename}' was successfully removed.`,
            level: "success"
          });
        }
        fetchFiles();
      } else {
        const errData = await res.json().catch(() => null);
        alert(`Failed to delete file: ${errData?.detail || res.statusText}`);
      }
    } catch (err) {
      alert(`Error deleting file: ${err.message}`);
    }
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'audio':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
        );
      case 'video':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
        );
      case 'image':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        );
      case 'database':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
          </svg>
        );
      case 'document':
      default:
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        );
    }
  };

  const getDownloadUrl = (filename) => {
    return `/api/download/${encodeURIComponent(filename)}?token=${encodeURIComponent(sessionToken)}`;
  };

  const filteredFiles = files.filter(f => {
    if (filterType === 'all') return true;
    return f.type === filterType;
  });

  return (
    <div className="workspace-explorer-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', padding: '0 4px' }}>
        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 700, color: 'var(--text-tertiary)' }}>
          {filterType === 'all' ? 'Library Files' : `${filterType}s`} ({filteredFiles.length})
        </span>
        <button
          onClick={fetchFiles}
          disabled={isLoading}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-tertiary)',
            cursor: 'pointer',
            padding: '2px',
            display: 'flex',
            alignItems: 'center',
            opacity: isLoading ? 0.5 : 1
          }}
          title="Refresh library"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px', animation: isLoading ? 'spin 1s linear infinite' : 'none' }}>
            <path d="M23 4v6h-6" />
            <path d="M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
      </div>

      {filteredFiles.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '24px 8px', color: '#555876', fontSize: '0.8rem', background: 'rgba(0,0,0,0.15)', borderRadius: '8px', border: '1px dashed rgba(255,255,255,0.03)' }}>
          {isLoading ? "Loading..." : `No ${filterType === 'all' ? 'files' : filterType + 's'} found.`}
        </div>
      ) : (
        <div 
          style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '6px', 
            maxHeight: '100%', 
            overflowY: 'auto',
          }}
          className="explorer-scroll-container"
        >
          {filteredFiles.map((file) => (
            <div
              key={file.filename}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                background: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid rgba(255, 255, 255, 0.03)',
                borderRadius: '8px',
                transition: 'all 0.2s ease',
                gap: '8px'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.01)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.03)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: 1 }}>
                <div style={{ flexShrink: 0 }}>
                  {getFileIcon(file.type)}
                </div>
                <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                  <a
                    href={getDownloadUrl(file.filename)}
                    download={file.filename}
                    title={file.filename}
                    style={{
                      fontSize: '0.8rem',
                      fontWeight: '500',
                      color: '#e8eaff',
                      textDecoration: 'none',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'block'
                    }}
                  >
                    {file.filename}
                  </a>
                  <span style={{ fontSize: '0.65rem', color: '#64748b' }}>
                    {formatBytes(file.size)}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '2px', flexShrink: 0 }}>
                {/* Download Button */}
                <a
                  href={getDownloadUrl(file.filename)}
                  download={file.filename}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: '3px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                  title="Download"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px' }}>
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                </a>
                
                {/* Delete Button */}
                <button
                  onClick={() => handleDelete(file.filename)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: '3px',
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                  title="Delete file"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px' }}>
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
