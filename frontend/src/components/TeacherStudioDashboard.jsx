import React, { useState } from 'react';
import CockpitOverviewModule from './teacher/CockpitOverviewModule';
import PaperSetterModule from './teacher/PaperSetterModule';
import SmartDiaryModule from './teacher/SmartDiaryModule';
import PrivateMarkbookModule from './teacher/PrivateMarkbookModule';

const MODULES = [
  { id: 'overview', name: 'AI Cockpit Overview', emoji: '🏠', color: '#a78bfa' },
  { id: 'paper_setter', name: 'Paper Setter & Activity Designer', emoji: '⚡', color: '#fbbf24' },
  { id: 'smart_diary', name: 'Smart Diary & Coordinator', emoji: '📅', color: '#a78bfa' },
  { id: 'private_markbook', name: 'Private Markbook & OCR Ledger', emoji: '📊', color: '#10b981' }
];

export default function TeacherStudioDashboard({ onSend, isLoading, onUpload, isUploading }) {
  const [activeModule, setActiveModule] = useState('overview');
  const [generatedDocs, setGeneratedDocs] = useState([]);
  const [sessionUploads, setSessionUploads] = useState([]);

  const logGeneratedDoc = (name, service) => {
    setGeneratedDocs(prev => [{ name, service, date: 'Just now' }, ...prev]);
  };

  const logUpload = (fileName) => {
    setSessionUploads(prev => {
      if (prev.includes(fileName)) return prev;
      return [fileName, ...prev];
    });
  };

  const handleDashboardSend = (query) => {
    if (query.toLowerCase().includes("generate") || query.toLowerCase().includes("create") || query.toLowerCase().includes("export") || query.toLowerCase().includes("sync")) {
      let docName = "Grounded Academic Document";
      let service = "Google Docs";
      if (query.includes("Forms") || query.includes("quiz") || query.includes("Quiz")) {
        docName = "Competency Pop-Quiz";
        service = "Google Forms";
      } else if (query.includes("Bifurcation") || query.includes("ledger")) {
        docName = "Syllabus Bifurcation Ledger";
        service = "Google Docs";
      } else if (query.includes("Sheets") || query.includes("gradebook") || query.includes("spreadsheet")) {
        docName = "Private Class Gradebook";
        service = "Google Sheets";
      } else if (query.includes("Calendar") || query.includes("Schedule")) {
        docName = "Calendar Timetable Sync";
        service = "Google Calendar";
      }
      logGeneratedDoc(docName, service);
    }
    onSend(query);
  };

  const handleDashboardUpload = async (file) => {
    logUpload(file.name);
    if (onUpload) {
      await onUpload(file);
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
      {/* Top Suite Header */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9))',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '16px',
        padding: '20px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.25)',
        backdropFilter: 'blur(10px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '36px', filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.3))' }}>🇮🇳</span>
          <div>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: '800', color: '#fff', letterSpacing: '-0.5px' }}>
              The Streamlined Teacher's Personal AI Cockpit
            </h1>
            <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '13px' }}>
              Your unified autonomous executive workspace. Streamline paper setting, sync Google calendars, and OCR transcribe gradebook ledgers.
            </p>
          </div>
        </div>
      </div>

      {/* Module Navigation Tabs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '12px'
      }}>
        {MODULES.map((mod) => {
          const isActive = mod.id === activeModule;
          return (
            <button
              key={mod.id}
              onClick={() => setActiveModule(mod.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: '8px',
                padding: '16px 12px',
                borderRadius: '14px',
                border: isActive ? `2px solid ${mod.color}` : '1px solid rgba(255, 255, 255, 0.05)',
                background: isActive ? `radial-gradient(circle at center, ${mod.color}25, rgba(15, 23, 42, 0.95))` : 'rgba(30, 41, 59, 0.4)',
                cursor: 'pointer',
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                boxShadow: isActive ? `0 8px 24px ${mod.color}20, inset 0 0 8px ${mod.color}15` : 'none',
                transform: isActive ? 'translateY(-2px)' : 'none',
                textAlign: 'center'
              }}
            >
              <span style={{ fontSize: '24px', filter: isActive ? 'drop-shadow(0 0 8px currentColor)' : 'none' }}>{mod.emoji}</span>
              <span style={{ fontSize: '12px', fontWeight: '700', color: isActive ? '#fff' : '#94a3b8', letterSpacing: '0.2px' }}>
                {mod.name}
              </span>
            </button>
          );
        })}
      </div>

      {/* Render Selected Modular Window Form Component */}
      <div className="module-content-area" style={{ flex: 1, minHeight: 0 }}>
        {activeModule === 'overview' && (
          <CockpitOverviewModule 
            onSend={handleDashboardSend} 
            isLoading={isLoading} 
            setActiveModule={setActiveModule}
            generatedDocs={generatedDocs}
            sessionUploads={sessionUploads}
          />
        )}
        {activeModule === 'paper_setter' && (
          <PaperSetterModule 
            onSend={handleDashboardSend} 
            isLoading={isLoading} 
            onUpload={handleDashboardUpload} 
            isUploading={isUploading} 
          />
        )}
        {activeModule === 'smart_diary' && (
          <SmartDiaryModule 
            onSend={handleDashboardSend} 
            isLoading={isLoading} 
            onUpload={handleDashboardUpload} 
            isUploading={isUploading} 
          />
        )}
        {activeModule === 'private_markbook' && (
          <PrivateMarkbookModule 
            onSend={handleDashboardSend} 
            isLoading={isLoading} 
            onUpload={handleDashboardUpload} 
            isUploading={isUploading} 
          />
        )}
      </div>
    </div>
  );
}
