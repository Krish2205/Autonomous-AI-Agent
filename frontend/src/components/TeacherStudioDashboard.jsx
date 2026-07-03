import React, { useState } from 'react';
import TeacherWorkstation from './teacher/TeacherWorkstation';

export default function TeacherStudioDashboard({ onSend, isLoading, onUpload, isUploading }) {
  const [sessionUploads, setSessionUploads] = useState([]);

  const logUpload = (fileName) => {
    setSessionUploads(prev => {
      if (prev.includes(fileName)) return prev;
      return [fileName, ...prev];
    });
  };

  const handleDashboardSend = (query) => {
    onSend(query);
  };

  const handleDashboardUpload = async (file) => {
    logUpload(file.name);
    if (onUpload) {
      await onUpload(file, true);
    }
  };

  return (
    <div className="teacher-dashboard-container" style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      maxWidth: '1280px',
      margin: '0 auto',
      padding: '24px',
      gap: '24px',
      color: '#e2e8f0',
      overflowY: 'auto'
    }}>
      <div className="module-content-area" style={{ flex: 1, minHeight: 0 }}>
        <TeacherWorkstation 
          onSend={handleDashboardSend} 
          isLoading={isLoading} 
          onUpload={handleDashboardUpload} 
          isUploading={isUploading} 
        />
      </div>
    </div>
  );
}

