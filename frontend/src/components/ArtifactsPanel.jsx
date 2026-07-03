import React, { useState, useEffect } from 'react';

export default function ArtifactsPanel({ artifact, onClose }) {
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'code'

  useEffect(() => {
    // Default to 'code' if preview is not supported
    if (artifact && !['html', 'svg', 'csv'].includes(artifact.type)) {
      setActiveTab('code');
    } else {
      setActiveTab('preview');
    }
  }, [artifact]);

  if (!artifact) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    alert('Copied to clipboard!');
  };

  const handleDownload = () => {
    const blob = new Blob([artifact.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.name || 'artifact.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Helper to render CSV table
  const renderCSVTable = () => {
    const lines = artifact.content.trim().split('\n');
    if (lines.length === 0) return <p style={{ color: '#94a3b8' }}>Empty dataset</p>;
    
    // Parse headers (handling basic comma splitting)
    const headers = lines[0].split(',').map(h => h.replace(/^["']|["']$/g, '').trim());
    const rows = lines.slice(1).map(line => line.split(',').map(c => c.replace(/^["']|["']$/g, '').trim()));

    return (
      <div style={{ overflowX: 'auto', maxHeight: '100%', padding: '16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', color: '#e2e8f0' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #334155', textAlign: 'left', background: '#1e293b' }}>
              {headers.map((h, i) => (
                <th key={i} style={{ padding: '10px 12px', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? 'transparent' : '#0f172a' }}>
                {row.map((cell, i) => (
                  <td key={i} style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div style={{
      width: '50%',
      height: '100%',
      backgroundColor: '#0b0f19',
      borderLeft: '1px solid #1e293b',
      display: 'flex',
      flexDirection: 'column',
      color: '#e2e8f0',
      zIndex: 40,
      position: 'relative'
    }}>
      {/* Header bar */}
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#0d1324'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.2rem' }}>
            {artifact.type === 'html' ? '🌐' : artifact.type === 'csv' ? '📊' : artifact.type === 'svg' ? '🎨' : '📄'}
          </span>
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
              {artifact.title || 'Artifact'}
            </h3>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{artifact.name}</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button 
            onClick={handleCopy}
            title="Copy to Clipboard"
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid #1e293b',
              backgroundColor: '#131c31',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            📋 Copy
          </button>
          <button 
            onClick={handleDownload}
            title="Download file"
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid #1e293b',
              backgroundColor: '#131c31',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            💾 Download
          </button>
          <button 
            onClick={onClose}
            style={{
              padding: '6px 10px',
              border: 'none',
              backgroundColor: 'transparent',
              color: '#ef4444',
              cursor: 'pointer',
              fontSize: '1.2rem'
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Tabs */}
      {['html', 'svg', 'csv'].includes(artifact.type) && (
        <div style={{
          display: 'flex',
          borderBottom: '1px solid #1e293b',
          backgroundColor: '#0d1324',
          padding: '0 16px'
        }}>
          <button
            onClick={() => setActiveTab('preview')}
            style={{
              padding: '10px 16px',
              backgroundColor: 'transparent',
              border: 'none',
              color: activeTab === 'preview' ? '#38bdf8' : '#64748b',
              borderBottom: activeTab === 'preview' ? '2px solid #38bdf8' : 'none',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600
            }}
          >
            🖥️ Preview
          </button>
          <button
            onClick={() => setActiveTab('code')}
            style={{
              padding: '10px 16px',
              backgroundColor: 'transparent',
              border: 'none',
              color: activeTab === 'code' ? '#38bdf8' : '#64748b',
              borderBottom: activeTab === 'code' ? '2px solid #38bdf8' : 'none',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600
            }}
          >
            💻 Code
          </button>
        </div>
      )}

      {/* Pane Content */}
      <div style={{ flex: 1, overflow: 'hidden', backgroundColor: '#070a13' }}>
        {activeTab === 'preview' ? (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
            {artifact.type === 'html' && (
              <iframe
                title="Artifact Preview"
                srcDoc={artifact.content}
                sandbox="allow-scripts"
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  backgroundColor: '#ffffff'
                }}
              />
            )}
            {artifact.type === 'svg' && (
              <div 
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#0f172a',
                  padding: '20px'
                }}
                dangerouslySetInnerHTML={{ __html: artifact.content }}
              />
            )}
            {artifact.type === 'csv' && renderCSVTable()}
          </div>
        ) : (
          <pre style={{
            margin: 0,
            padding: '20px',
            overflow: 'auto',
            height: '100%',
            fontFamily: 'Consolas, Monaco, monospace',
            fontSize: '0.85rem',
            lineHeight: '1.5',
            color: '#a7f3d0',
            backgroundColor: '#070a13'
          }}>
            <code>{artifact.content}</code>
          </pre>
        )}
      </div>
    </div>
  );
}
