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
  const [previewFile, setPreviewFile] = useState(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textContent, setTextContent] = useState("");

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

  const isTextFile = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    return ['txt', 'py', 'js', 'json', 'html', 'css', 'log', 'csv', 'sh', 'md', 'yml', 'yaml', 'jsx'].includes(ext);
  };

  const handlePreviewClick = async (file) => {
    setPreviewFile(file);
    if (file.type === 'document' && isTextFile(file.filename)) {
      setTextLoading(true);
      setTextContent("");
      try {
        const res = await fetch(getDownloadUrl(file.filename));
        if (res.ok) {
          const text = await res.text();
          setTextContent(text);
        } else {
          setTextContent("Failed to load file contents.");
        }
      } catch (err) {
        setTextContent("Error reading file: " + err.message);
      } finally {
        setTextLoading(false);
      }
    }
  };

  const renderPreview = (file) => {
    const downloadUrl = getDownloadUrl(file.filename);
    switch (file.type) {
      case 'image':
        return (
          <img 
            src={downloadUrl} 
            alt={file.filename} 
            style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
            loading="lazy"
          />
        );
      case 'video':
        return (
          <video 
            src={downloadUrl} 
            style={{ width: '100%', height: '100%', objectFit: 'contain', pointerEvents: 'none' }} 
          />
        );
      case 'audio':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%', gap: '6px', background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.03), rgba(0, 0, 0, 0.2))' }}>
            <span style={{ fontSize: '1.8rem' }}>🎙️</span>
            <span style={{ fontSize: '0.6rem', color: '#64748b', fontWeight: '500' }}>Audio clip</span>
          </div>
        );
      case 'database':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
            <span style={{ fontSize: '2rem' }}>🗄️</span>
            <span style={{ fontSize: '0.58rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: '#64748b', fontWeight: 'bold' }}>Database</span>
          </div>
        );
      case 'document':
      default: {
        const ext = file.filename.split('.').pop().toLowerCase();
        let docIcon = '📄';
        if (ext === 'pdf') docIcon = '📕';
        else if (ext === 'csv' || ext === 'xlsx') docIcon = '📊';
        else if (ext === 'json') docIcon = '🔤';
        else if (ext === 'py' || ext === 'js' || ext === 'html' || ext === 'css') docIcon = '💻';
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
            <span style={{ fontSize: '2rem' }}>{docIcon}</span>
            <span style={{ fontSize: '0.58rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: '#64748b', fontWeight: 'bold' }}>{ext} Document</span>
          </div>
        );
      }
    }
  };

  const filteredFiles = files.filter(f => {
    if (filterType === 'all') return true;
    return f.type === filterType;
  });

  return (
    <div className="workspace-explorer-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}>
      <style>{`
        .files-grid {
          display: grid !important;
          grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)) !important;
          grid-auto-rows: max-content !important;
          gap: 14px !important;
          overflow-y: auto !important;
          flex: 1 !important;
          padding-bottom: 20px !important;
        }
        .file-card {
          background: rgba(255, 255, 255, 0.015);
          border: 1px solid rgba(255, 255, 255, 0.04);
          border-radius: 12px;
          padding: 10px;
          display: flex;
          flex-direction: column;
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
          box-sizing: border-box;
          position: relative;
          cursor: pointer;
        }
        .file-card:hover {
          background: rgba(255, 255, 255, 0.03) !important;
          border-color: rgba(0, 212, 255, 0.15) !important;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
          transform: translateY(-2px);
        }
        .file-preview-container {
          height: 120px;
          width: 100%;
          overflow: hidden;
          border-radius: 8px;
          background: #070a13;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(255, 255, 255, 0.03);
        }
        .file-action-btn {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          color: #cbd5e1;
          cursor: pointer;
          padding: 5px 7px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          transition: all 0.2s ease;
        }
        .file-action-btn:hover {
          background: rgba(255, 255, 255, 0.08) !important;
          color: #fff !important;
        }
        .file-action-btn.delete:hover {
          background: rgba(244, 63, 94, 0.15) !important;
          color: rgba(244, 63, 94, 1) !important;
        }
        .preview-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: rgba(4, 6, 12, 0.85);
          backdrop-filter: blur(16px);
          z-index: 2000;
          display: flex;
          align-items: center;
          justify-content: center;
          animation: overlayFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .preview-modal-container {
          background: rgba(13, 18, 30, 0.95);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          width: 80%;
          max-width: 900px;
          height: 80%;
          max-height: 700px;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
          overflow: hidden;
          animation: drawerSlideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .preview-modal-header {
          padding: 16px 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .preview-modal-body {
          flex: 1;
          overflow: auto;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #040711;
          padding: 20px;
          position: relative;
        }
        .preview-modal-footer {
          padding: 16px 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: rgba(13, 18, 30, 0.5);
        }
        .code-preview-block {
          width: 100%;
          height: 100%;
          margin: 0;
          padding: 14px;
          background: #040711;
          color: #34d399;
          font-family: var(--font-mono, monospace);
          font-size: 0.78rem;
          line-height: 1.5;
          overflow: auto;
          text-align: left;
          white-space: pre-wrap;
          box-sizing: border-box;
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.03);
        }
      `}</style>

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
        <div className="files-grid explorer-scroll-container">
          {filteredFiles.map((file) => (
            <div key={file.filename} className="file-card" onClick={() => handlePreviewClick(file)}>
              <div className="file-preview-container">
                {renderPreview(file)}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', marginTop: '10px', gap: '2px', minWidth: 0 }}>
                <span
                  title={file.filename}
                  style={{
                    fontSize: '0.74rem',
                    fontWeight: '600',
                    color: '#f1f5f9',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    display: 'block'
                  }}
                >
                  {file.filename}
                </span>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }} onClick={(e) => e.stopPropagation()}>
                  <span style={{ fontSize: '0.64rem', color: '#64748b' }}>
                    {formatBytes(file.size)}
                  </span>
                  
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <a
                      href={getDownloadUrl(file.filename)}
                      download={file.filename}
                      className="file-action-btn"
                      title="Download"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: '10px', height: '10px' }}>
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                    </a>
                    <button
                      onClick={() => handleDelete(file.filename)}
                      className="file-action-btn delete"
                      title="Delete file"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: '10px', height: '10px' }}>
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Lightbox / Preview Modal */}
      {previewFile && (
        <div className="preview-modal-overlay" onClick={() => setPreviewFile(null)}>
          <div className="preview-modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="preview-modal-header">
              <div>
                <h3 style={{ margin: 0, color: '#f1f5f9', fontSize: '0.95rem' }}>
                  🔍 Preview: {previewFile.filename}
                </h3>
                <span style={{ fontSize: '0.66rem', color: '#64748b' }}>
                  {previewFile.type.toUpperCase()} file
                </span>
              </div>
              <button 
                onClick={() => setPreviewFile(null)}
                style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div className="preview-modal-body">
              {previewFile.type === 'image' && (
                <img 
                  src={getDownloadUrl(previewFile.filename)} 
                  alt={previewFile.filename} 
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: '8px' }} 
                />
              )}
              {previewFile.type === 'video' && (
                <video 
                  src={getDownloadUrl(previewFile.filename)} 
                  controls 
                  autoPlay
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} 
                />
              )}
              {previewFile.type === 'audio' && (
                <div style={{ width: '80%', textAlign: 'center' }}>
                  <span style={{ fontSize: '3rem', display: 'block', marginBottom: '16px' }}>🎙️</span>
                  <audio src={getDownloadUrl(previewFile.filename)} controls autoPlay style={{ width: '100%' }} />
                </div>
              )}
              {previewFile.type === 'document' && (
                isTextFile(previewFile.filename) ? (
                  textLoading ? (
                    <div style={{ color: '#64748b', fontSize: '0.8rem' }}>Loading content...</div>
                  ) : (
                    <pre className="code-preview-block">{textContent}</pre>
                  )
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
                    <span style={{ fontSize: '3rem', display: 'block', marginBottom: '12px' }}>📄</span>
                    <p style={{ fontSize: '0.8rem', margin: '0 0 16px 0' }}>Interactive preview not available for this document type.</p>
                    <a
                      href={getDownloadUrl(previewFile.filename)}
                      download={previewFile.filename}
                      className="file-action-btn"
                      style={{ display: 'inline-flex', gap: '6px', fontSize: '0.78rem', padding: '8px 16px' }}
                    >
                      Download to view
                    </a>
                  </div>
                )
              )}
              {previewFile.type === 'database' && (
                <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
                  <span style={{ fontSize: '3rem', display: 'block', marginBottom: '12px' }}>🗄️</span>
                  <p style={{ fontSize: '0.8rem', margin: '0 0 16px 0' }}>Previewing raw database contents is not supported.</p>
                  <a
                    href={getDownloadUrl(previewFile.filename)}
                    download={previewFile.filename}
                    className="file-action-btn"
                    style={{ display: 'inline-flex', gap: '6px', fontSize: '0.78rem', padding: '8px 16px' }}
                  >
                    Download Database File
                  </a>
                </div>
              )}
            </div>

            <div className="preview-modal-footer">
              <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                Size: {formatBytes(previewFile.size)}
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <a
                  href={getDownloadUrl(previewFile.filename)}
                  download={previewFile.filename}
                  className="file-action-btn"
                  style={{ padding: '8px 14px', fontSize: '0.76rem' }}
                >
                  Download
                </a>
                <button
                  onClick={() => {
                    handleDelete(previewFile.filename);
                    setPreviewFile(null);
                  }}
                  className="file-action-btn delete"
                  style={{ padding: '8px 14px', fontSize: '0.76rem' }}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
