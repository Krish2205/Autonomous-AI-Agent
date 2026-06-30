import React, { useState } from 'react';

export default function SmartDiaryModule({ onSend, isLoading, onUpload, isUploading }) {
  const [syllabusProgress, setSyllabusProgress] = useState(0);
  const [uploadedSyllabus, setUploadedSyllabus] = useState('');
  const [timetable, setTimetable] = useState([]);
  
  // Builder inputs
  const [period, setPeriod] = useState('Period 1 (09:00 AM)');
  const [className, setClassName] = useState('');
  const [topicName, setTopicName] = useState('');

  const handleSyllabusChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadedSyllabus(file.name);
    setSyllabusProgress(30); // Grounded progress initialized
    if (onUpload) {
      await onUpload(file);
    }
  };

  const handleAddPeriod = (e) => {
    e.preventDefault();
    if (!className.trim() || !topicName.trim()) return;
    const newSlot = {
      period,
      class: className,
      topic: topicName,
      status: 'Upcoming'
    };
    setTimetable(prev => [...prev, newSlot]);
    setClassName('');
    setTopicName('');
  };

  const handleCreateBifurcation = () => {
    if (!uploadedSyllabus) {
      alert("Please upload a syllabus file first to ground the planning.");
      return;
    }
    onSend(`Using RAG, read the uploaded syllabus file "${uploadedSyllabus}", and generate the annual Syllabus Bifurcation ledger document mapping remaining units to school working days, and append it to Google Docs.`);
  };

  const handleSyncCalendar = (slot) => {
    if (!uploadedSyllabus) {
      alert("Please upload a syllabus file first to ground the planning.");
      return;
    }
    onSend(`Using RAG, cross-reference the uploaded syllabus file "${uploadedSyllabus}" and schedule Period: "${slot.class} - ${slot.topic}" for today starting at ${slot.period.match(/\(([^)]+)\)/)?.[1] || '09:00 AM'} on Google Calendar.`);
  };

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.75)', border: '1px solid rgba(139, 92, 246, 0.4)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', boxShadow: '0 12px 32px rgba(0,0,0,0.3)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '22px', color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '10px' }}>
            📅 Smart Diary & Calendar Coordinator (RAG Grounded)
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Internal Records Engine. Upload your curriculum syllabus files to auto-plan timelines and diary entries grounded strictly on the material.
          </p>
        </div>
      </div>

      {/* RAG Syllabus Upload Section */}
      <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(167, 139, 250, 0.2)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <label style={{ fontSize: '13px', color: '#a78bfa', fontWeight: 'bold' }}>📖 Grounding Syllabus Source (RAG File):</label>
        <div style={{
          border: '2px dashed rgba(167, 139, 250, 0.4)',
          borderRadius: '10px',
          padding: '20px 10px',
          textAlign: 'center',
          background: 'rgba(30, 41, 59, 0.4)',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{ fontSize: '26px' }}>📁</span>
          <div style={{ fontSize: '12px', color: '#cbd5e1', wordBreak: 'break-all' }}>
            {isUploading ? "Uploading syllabus document..." : uploadedSyllabus ? `Grounded Syllabus: ${uploadedSyllabus}` : "Drag & drop syllabus PDF, Word, or course syllabus ledger here"}
          </div>
          <input
            type="file"
            accept=".pdf,.txt,.docx"
            onChange={handleSyllabusChange}
            style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              opacity: 0,
              cursor: 'pointer'
            }}
          />
          {!isUploading && !uploadedSyllabus && (
            <span style={{ padding: '4px 12px', borderRadius: '6px', background: 'rgba(167, 139, 250, 0.15)', color: '#c084fc', fontSize: '11px', border: '1px solid rgba(167, 139, 250, 0.3)', pointerEvents: 'none' }}>
              Select Syllabus File
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px' }}>
        {/* Left Side: Daily Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Add Timetable Period Builder */}
          <form onSubmit={handleAddPeriod} style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <h4 style={{ margin: 0, fontSize: '13px', color: '#a78bfa' }}>➕ Add Timetable Class Entry</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr 1.2fr', gap: '10px' }}>
              <select value={period} onChange={e => setPeriod(e.target.value)} style={{ padding: '8px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '6px' }}>
                <option value="Period 1 (09:00 AM)">Period 1 (09:00 AM)</option>
                <option value="Period 2 (10:00 AM)">Period 2 (10:00 AM)</option>
                <option value="Period 3 (11:15 AM)">Period 3 (11:15 AM)</option>
                <option value="Period 4 (01:30 PM)">Period 4 (01:30 PM)</option>
              </select>
              <input type="text" placeholder="Class (e.g. Class 10A)" value={className} onChange={e => setClassName(e.target.value)} style={{ padding: '8px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '6px' }} />
              <input type="text" placeholder="Topic (e.g. Chemical Formulas)" value={topicName} onChange={e => setTopicName(e.target.value)} style={{ padding: '8px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '6px' }} />
            </div>
            <button type="submit" style={{ alignSelf: 'flex-end', padding: '6px 16px', background: '#a78bfa', border: 'none', color: '#0f172a', fontWeight: 'bold', fontSize: '12px', borderRadius: '6px', cursor: 'pointer' }}>
              Add Period Slot
            </button>
          </form>

          {/* Daily Schedule Slots */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(167, 139, 250, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#a78bfa' }}>⏱️ Daily Period Ledger & Calendar Sync</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {timetable.length > 0 ? (
                timetable.map((slot, index) => (
                  <div key={index} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(30, 41, 59, 0.5)',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255,255,255,0.03)'
                  }}>
                    <div>
                      <span style={{ fontSize: '11px', color: '#94a3b8', display: 'block' }}>{slot.period}</span>
                      <strong style={{ fontSize: '14px', color: '#fff' }}>{slot.class}</strong>
                      <span style={{ fontSize: '12px', color: '#cbd5e1', display: 'block', marginTop: '2px' }}>Topic: {slot.topic}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        fontWeight: 'bold',
                        background: 'rgba(255,255,255,0.05)',
                        color: '#cbd5e1'
                      }}>
                        {slot.status}
                      </span>
                      <button
                        onClick={() => handleSyncCalendar(slot)}
                        disabled={isLoading || isUploading || !uploadedSyllabus}
                        style={{
                          background: uploadedSyllabus ? 'rgba(167, 139, 250, 0.2)' : 'rgba(255,255,255,0.04)',
                          border: uploadedSyllabus ? '1px solid rgba(167, 139, 250, 0.3)' : '1px solid rgba(255,255,255,0.05)',
                          borderRadius: '6px',
                          color: uploadedSyllabus ? '#c084fc' : '#64748b',
                          padding: '4px 8px',
                          fontSize: '11px',
                          cursor: uploadedSyllabus ? 'pointer' : 'not-allowed'
                        }}
                      >
                        Sync
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '13px', color: '#94a3b8', padding: '16px 0', textAlign: 'center' }}>
                  No periods configured for today yet. Use the entry form above to add periods.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Syllabus Bifurcation Tracker */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(167, 139, 250, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#a78bfa' }}>📊 Syllabus Bifurcation Ledger</h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Overall Target Completion:</span>
              <strong style={{ fontSize: '16px', color: '#10b981' }}>{syllabusProgress}%</strong>
            </div>
            
            <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${syllabusProgress}%`, height: '100%', background: '#10b981' }} />
            </div>

            <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.4', marginTop: '6px' }}>
              {uploadedSyllabus ? `Grounded plan parsed from "${uploadedSyllabus}".` : "Please upload a syllabus file to auto-calculate targets."}
            </div>

            <button
              onClick={handleCreateBifurcation}
              disabled={isLoading || isUploading || !uploadedSyllabus}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                background: uploadedSyllabus ? '#a78bfa' : 'rgba(255,255,255,0.06)',
                color: uploadedSyllabus ? '#0f172a' : '#64748b',
                border: 'none',
                fontWeight: '700',
                fontSize: '12px',
                cursor: uploadedSyllabus ? 'pointer' : 'not-allowed',
                marginTop: '10px'
              }}
            >
              {uploadedSyllabus ? "📑 Generate Syllabus Bifurcation Ledgers" : "⚠️ Please upload syllabus first"}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
