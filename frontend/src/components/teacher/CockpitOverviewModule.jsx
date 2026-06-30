import React from 'react';

export default function CockpitOverviewModule({ onSend, isLoading, setActiveModule, generatedDocs = [], sessionUploads = [] }) {
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
      {/* Welcome Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(167, 139, 250, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)',
        border: '1px solid rgba(167, 139, 250, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 8px 32px rgba(167, 139, 250, 0.1)'
      }}>
        <h2 style={{ margin: '0 0 6px 0', fontSize: '22px', color: '#a78bfa' }}>
          Personal AI Cockpit Control Board
        </h2>
        <p style={{ margin: 0, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>
          Welcome, Monica. Your unified GenAI Engine and Internal Records workspace is online. You are currently connected to Google Docs, Calendar, Sheets, and Drive APIs.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px' }}>
        {/* Left Column: GenAI Engine Status & Internal Records Overview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Quick Engine Status Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* GenAI Engine Summary */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.75)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '16px',
              padding: '20px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#fbbf24' }}>⚡ Core GenAI Engine</h3>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fff', marginBottom: '4px' }}>RAG Engine</div>
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                {sessionUploads.length > 0 ? `${sessionUploads.length} Reference File(s) Active` : 'No Grounding Files'}
              </span>
              <button 
                onClick={() => setActiveModule('paper_setter')}
                style={{
                  width: '100%',
                  marginTop: '16px',
                  padding: '8px',
                  borderRadius: '8px',
                  background: 'rgba(251, 191, 36, 0.15)',
                  border: '1px solid rgba(251, 191, 36, 0.3)',
                  color: '#fbbf24',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Go to Paper Setter →
              </button>
            </div>

            {/* Internal Records Summary */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.75)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '16px',
              padding: '20px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#10b981' }}>📊 Internal Records Engine</h3>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#fff', marginBottom: '4px' }}>Syllabus Sync</div>
              <span style={{ fontSize: '12px', color: '#cbd5e1' }}>Live Calendar Coordination</span>
              <button 
                onClick={() => setActiveModule('smart_diary')}
                style={{
                  width: '100%',
                  marginTop: '16px',
                  padding: '8px',
                  borderRadius: '8px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  color: '#10b981',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Open Smart Diary →
              </button>
            </div>
          </div>

          {/* Action Required Alert Box */}
          <div style={{
            background: 'rgba(30, 41, 59, 0.75)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 12px 32px rgba(0,0,0,0.3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#38bdf8' }}>⚡ Active Grounding Alerts</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {sessionUploads.length > 0 ? (
                <div style={{
                  background: 'rgba(15, 23, 42, 0.4)',
                  borderLeft: '4px solid #38bdf8',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <div style={{ flex: 1 }}>
                    <strong style={{ display: 'block', fontSize: '13px', color: '#fff', marginBottom: '2px' }}>Reference Data Ready</strong>
                    <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                      Ready to build grounded papers or diary events from: {sessionUploads.map(f => `"${f}"`).join(', ')}.
                    </span>
                  </div>
                  <button
                    onClick={() => setActiveModule('paper_setter')}
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: 'none',
                      color: '#fff',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    Go Build
                  </button>
                </div>
              ) : (
                <div style={{ fontSize: '13px', color: '#94a3b8', padding: '10px 0', textAlign: 'center' }}>
                  No active reference files uploaded in this session. Upload a document in Paper Setter or Smart Diary to start RAG.
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Right Column: Google Drive / Docs Activity Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{
            background: 'rgba(30, 41, 59, 0.75)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 12px 32px rgba(0,0,0,0.3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
            flex: 1
          }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#a78bfa' }}>📂 Session Google Drive Syncs</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {generatedDocs.length > 0 ? (
                generatedDocs.map((doc, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: 'rgba(15, 23, 42, 0.4)',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255,255,255,0.02)'
                  }}>
                    <div>
                      <strong style={{ color: '#fff', fontSize: '13px', display: 'block' }}>{doc.name}</strong>
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>Synced to {doc.service}</span>
                    </div>
                    <span style={{ fontSize: '11px', color: '#94a3b8' }}>{doc.date}</span>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '13px', color: '#94a3b8', padding: '20px 0', textAlign: 'center' }}>
                  No files synchronized to Google Drive in this session yet.
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
