import React, { useState } from 'react';

export default function PrivateMarkbookModule({ onSend, isLoading, onUpload, isUploading }) {
  const [spreadsheetTitle, setSpreadsheetTitle] = useState('Class 10A Science Gradebook');
  const [uploadedMarksheet, setUploadedMarksheet] = useState('');
  const [grades, setGrades] = useState([]);

  // Student row builder inputs
  const [roll, setRoll] = useState('');
  const [name, setName] = useState('');
  const [quiz1, setQuiz1] = useState(0);
  const [midterm, setMidterm] = useState(0);

  const handleAddStudent = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    const finalRoll = roll.trim() || `10${grades.length + 1}`;
    const avg = (Number(quiz1) + Number(midterm)) / 2;
    const newStudent = {
      roll: finalRoll,
      name: name.trim(),
      homework: 'Submitted',
      quiz1: Number(quiz1),
      midterm: Number(midterm),
      status: avg < 75 ? 'Remedial Alert' : 'On Track'
    };
    setGrades(prev => [...prev, newStudent]);
    setRoll('');
    setName('');
    setQuiz1(0);
    setMidterm(0);
  };

  const handleUpdateGrade = (studentRoll, field, val) => {
    setGrades(prev => prev.map(student => {
      if (student.roll === studentRoll) {
        const nextGrades = { ...student, [field]: val };
        const avg = (Number(nextGrades.quiz1) + Number(nextGrades.midterm)) / 2;
        nextGrades.status = avg < 75 ? 'Remedial Alert' : 'On Track';
        return nextGrades;
      }
      return student;
    }));
  };

  const handleSyncSheets = () => {
    if (grades.length === 0) {
      alert("Please add at least one student record before syncing.");
      return;
    }
    const formattedData = grades.map(g => `${g.roll} | ${g.name} | ${g.homework} | Quiz1:${g.quiz1} | Midterm:${g.midterm} | ${g.status}`).join('\n');
    onSend(`Export the following student private gradebook marksheet data directly to Google Sheets spreadsheet titled "${spreadsheetTitle}":\n${formattedData}`);
  };

  const handleOCRFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadedMarksheet(file.name);
    if (onUpload) {
      await onUpload(file);
    }
  };

  const handleRunOCR = () => {
    if (!uploadedMarksheet) {
      alert("Please upload a handwritten marksheet photo first.");
      return;
    }
    onSend(`Perform OCR layout transcription on the uploaded student marksheet image "${uploadedMarksheet}". Transcribe names and marks and return a structured JSON mapping.`);
  };

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.75)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', boxShadow: '0 12px 32px rgba(0,0,0,0.3)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '22px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '10px' }}>
            📊 Private Markbook & OCR Ledger
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Internal Records Engine. Maintain private gradebooks, sync with Google Sheets, and OCR transcribe handwritten mark list photos.
          </p>
        </div>
        <button
          onClick={handleSyncSheets}
          disabled={isLoading || grades.length === 0}
          style={{
            padding: '10px 18px',
            borderRadius: '8px',
            background: grades.length === 0 ? 'rgba(255,255,255,0.04)' : '#10b981',
            color: grades.length === 0 ? '#64748b' : '#fff',
            border: 'none',
            fontWeight: '600',
            fontSize: '13px',
            cursor: grades.length === 0 ? 'not-allowed' : 'pointer',
            boxShadow: grades.length === 0 ? 'none' : '0 4px 14px rgba(16, 185, 129, 0.4)'
          }}
        >
          📊 Sync Live to Google Sheets
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px' }}>
        {/* Left Side: Spreadsheet Data-grid */}
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#10b981' }}>📝 Local Roster Grade Ledger</h3>
            <input
              type="text"
              value={spreadsheetTitle}
              onChange={e => setSpreadsheetTitle(e.target.value)}
              style={{
                background: 'rgba(30, 41, 59, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                padding: '4px 8px',
                color: '#fff',
                fontSize: '12px',
                width: '200px'
              }}
            />
          </div>

          {/* Quick Entry Form */}
          <form onSubmit={handleAddStudent} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr 1fr auto', gap: '8px', padding: '10px', background: 'rgba(15,23,42,0.4)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
            <input type="text" placeholder="Roll" value={roll} onChange={e => setRoll(e.target.value)} style={{ padding: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '4px' }} />
            <input type="text" placeholder="Student Name" value={name} onChange={e => setName(e.target.value)} style={{ padding: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '4px' }} />
            <input type="number" placeholder="Quiz 1" value={quiz1 || ''} onChange={e => setQuiz1(Number(e.target.value))} style={{ padding: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '4px' }} />
            <input type="number" placeholder="Midterm" value={midterm || ''} onChange={e => setMidterm(Number(e.target.value))} style={{ padding: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '4px' }} />
            <button type="submit" style={{ padding: '6px 12px', background: '#10b981', border: 'none', color: '#fff', fontSize: '12px', fontWeight: 'bold', borderRadius: '4px', cursor: 'pointer' }}>Add</button>
          </form>

          <div style={{ overflowX: 'auto' }}>
            {grades.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8' }}>
                    <th style={{ padding: '6px' }}>Roll</th>
                    <th style={{ padding: '6px' }}>Student Name</th>
                    <th style={{ padding: '6px' }}>Homework</th>
                    <th style={{ padding: '6px' }}>Quiz 1</th>
                    <th style={{ padding: '6px' }}>Midterm</th>
                    <th style={{ padding: '6px' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {grades.map(row => (
                    <tr key={row.roll} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', color: '#e2e8f0' }}>
                      <td style={{ padding: '8px 6px' }}>{row.roll}</td>
                      <td style={{ padding: '8px 6px', fontWeight: 'bold' }}>{row.name}</td>
                      <td style={{ padding: '8px 6px' }}>
                        <select value={row.homework} onChange={e => handleUpdateGrade(row.roll, 'homework', e.target.value)} style={{ background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', borderRadius: '4px' }}>
                          <option value="Submitted">Submitted</option>
                          <option value="Pending">Pending</option>
                        </select>
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        <input type="number" value={row.quiz1} onChange={e => handleUpdateGrade(row.roll, 'quiz1', Number(e.target.value))} style={{ width: '50px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', padding: '2px', borderRadius: '4px' }} />
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        <input type="number" value={row.midterm} onChange={e => handleUpdateGrade(row.roll, 'midterm', Number(e.target.value))} style={{ width: '50px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '12px', padding: '2px', borderRadius: '4px' }} />
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '10px',
                          fontSize: '11px',
                          fontWeight: 'bold',
                          background: row.status === 'On Track' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: row.status === 'On Track' ? '#34d399' : '#f87171'
                        }}>
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ padding: '20px 0', textColors: '#94a3b8', textAlign: 'center', fontSize: '13px' }}>
                Gradebook ledger empty. Add students manually above or upload a handwritten sheet photo below to OCR transcribe.
              </div>
            )}
          </div>
        </div>

        {/* Right Side: OCR Upload Photo Area */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', color: '#10b981' }}>📷 Vision OCR Ledger Ingestion</h3>
            
            <div style={{
              border: '2px dashed rgba(16, 185, 129, 0.4)',
              borderRadius: '10px',
              padding: '30px 15px',
              textAlign: 'center',
              background: 'rgba(30, 41, 59, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '10px',
              position: 'relative'
            }}>
              <span style={{ fontSize: '32px' }}>📷</span>
              <div style={{ fontSize: '12px', color: '#cbd5e1', wordBreak: 'break-all' }}>
                {isUploading ? "Uploading file..." : uploadedMarksheet ? `Loaded: ${uploadedMarksheet}` : "Drag & drop handwritten marksheet photo or CSV here"}
              </div>
              <input
                type="file"
                accept="image/*,.pdf,.csv"
                onChange={handleOCRFileChange}
                style={{
                  position: 'absolute',
                  width: '100%',
                  height: '100%',
                  opacity: 0,
                  cursor: 'pointer'
                }}
              />
              {!isUploading && !uploadedMarksheet && (
                <button style={{ padding: '8px 16px', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: '1px solid #10b981', fontSize: '12px', fontWeight: '600', pointerEvents: 'none' }}>
                  Upload Image
                </button>
              )}
            </div>

            <button
              onClick={handleRunOCR}
              disabled={isLoading || isUploading || !uploadedMarksheet}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                background: uploadedMarksheet ? '#10b981' : 'rgba(16, 185, 129, 0.3)',
                color: uploadedMarksheet ? '#fff' : '#64748b',
                border: 'none',
                fontWeight: '700',
                fontSize: '12px',
                cursor: uploadedMarksheet ? 'pointer' : 'not-allowed'
              }}
            >
              {uploadedMarksheet ? "🔍 Run AI OCR Transcription" : "📷 Upload image to run OCR"}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
