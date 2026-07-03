// ArtifactPanel.jsx
import React from 'react';

// This component displays a live preview of artifacts (e.g., rendered HTML, charts, SVGs)
// It receives the selected artifact content as HTML string via props.
export default function ArtifactPanel({ artifactHtml }) {
  return (
    <div className="artifact-panel">
      <style>{`
        .artifact-panel {
          flex: 1;
          background: rgba(20, 20, 30, 0.85);
          border-left: 1px solid rgba(100, 120, 255, 0.2);
          border-radius: 12px;
          padding: 16px;
          overflow-y: auto;
          color: #e8eaff;
          font-family: 'Inter', system-ui, sans-serif;
        }
        .artifact-content {
          animation: fadeIn 0.3s ease-in-out;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
      <div className="artifact-content" dangerouslySetInnerHTML={{ __html: artifactHtml || '<p>No artifact selected.</p>' }} />
    </div>
  );
}
