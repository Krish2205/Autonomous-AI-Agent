import React, { useState } from 'react';

export default function TeacherWorkstation({ onSend, isLoading, onUpload, isUploading }) {
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [activeLessonPlan, setActiveLessonPlan] = useState(null);
  const [isEditingTable, setIsEditingTable] = useState(false);
  const [activeTabId, setActiveTabId] = useState('teacher-1');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  
  const [isDocOpen, setIsDocOpen] = useState(false);
  const [activeDocTabId, setActiveDocTabId] = useState('doc-1');
  const [isSyncingDoc, setIsSyncingDoc] = useState(false);
  const [syncDocSuccess, setSyncDocSuccess] = useState(false);
  const [isPreviewDocMode, setIsPreviewDocMode] = useState(false);

  const [isTestsOpen, setIsTestsOpen] = useState(false);
  const [activeTestsTabId, setActiveTestsTabId] = useState('test-1');
  const [isSyncingTests, setIsSyncingTests] = useState(false);
  const [syncTestsSuccess, setSyncTestsSuccess] = useState(false);
  const [isPreviewTestsMode, setIsPreviewTestsMode] = useState(false);
  const [googleWeeklyTests, setGoogleWeeklyTests] = useState([
    {
      id: 'test-1',
      name: 'Weekly Test 1',
      content: 'Welcome to Weekly Tests. Click Save to Docs to sync with your Google account!',
      docUrl: null
    }
  ]);

  const [isWorksheetsOpen, setIsWorksheetsOpen] = useState(false);
  const [activeWorksheetsTabId, setActiveWorksheetsTabId] = useState('worksheet-1');
  const [isSyncingWorksheets, setIsSyncingWorksheets] = useState(false);
  const [syncWorksheetsSuccess, setSyncWorksheetsSuccess] = useState(false);
  const [isPreviewWorksheetsMode, setIsPreviewWorksheetsMode] = useState(false);
  const [googleWorksheets, setGoogleWorksheets] = useState([
    {
      id: 'worksheet-1',
      name: 'Worksheet 1',
      content: 'Welcome to Worksheets. Click Save to Docs to sync with your Google account!',
      docUrl: null
    }
  ]);
  
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [promptType, setPromptType] = useState('sheet'); // 'sheet', 'doc', 'weekly_tests', 'worksheets'
  const [promptValue, setPromptValue] = useState('');

  const [googleDocs, setGoogleDocs] = useState([
    {
      id: 'doc-1',
      name: 'Time Table Doc',
      content: 'Welcome to Google Docs Integration. Click Save to Docs to sync with your Google account!',
      docUrl: null
    }
  ]);
  
  const [timetables, setTimetables] = useState([
    {
      id: 'teacher-1',
      name: 'Time Table',
      data: [
        { time: '', mon: '', tue: '', wed: '', thu: '', fri: '', sat: '' }
      ]
    }
  ]);

  const activeTableData = timetables.find(t => t.id === activeTabId)?.data || [];

  const handleTableChange = (idx, field, value) => {
    setTimetables(prev => prev.map(t => {
      if (t.id === activeTabId) {
        const newData = [...t.data];
        newData[idx] = { ...newData[idx], [field]: value };
        return { ...t, data: newData };
      }
      return t;
    }));
  };

  const tasks = [
    { id: 'timetable', name: 'Sheets', emoji: '📊', desc: 'Manage and sync Google Sheets data' },
    { id: 'docs', name: 'Docs', emoji: '📝', desc: 'Manage and sync Google Docs data' },
    { id: 'weekly_tests', name: 'Weekly Tests', emoji: '⚡', desc: 'Generate custom test papers & answers' },
    { id: 'worksheets', name: 'Worksheets', emoji: '📝', desc: 'Design practice question worksheets' }
  ];



  const handleCellClick = (cellText) => {
    const nonLessonSubjects = ['Break', 'Lunch', 'Free', 'Planning Period', 'Planning', 'Staff Meeting'];
    if (nonLessonSubjects.includes(cellText)) return;
    
    let parsedGrade = 'General';
    let parsedSubject = cellText;
    
    if (cellText.includes(' - ')) {
      const parts = cellText.split(' - ');
      parsedGrade = parts[0].trim();
      parsedSubject = parts[1].trim();
    }
    
    setActiveLessonPlan({ grade: parsedGrade, subject: parsedSubject });
  };

  const handlePromptConfirm = () => {
    if (!promptValue.trim()) return;
    const name = promptValue.trim();
    if (promptType === 'sheet') {
      const newId = `teacher-${Date.now()}`;
      const skeletonData = [{ time: '', mon: '', tue: '', wed: '', thu: '', fri: '', sat: '' }];
      setTimetables(prev => [...prev, {
        id: newId,
        name: name,
        data: skeletonData
      }]);
      setActiveTabId(newId);
    } else if (promptType === 'doc') {
      const newId = `doc-${Date.now()}`;
      setGoogleDocs(prev => [...prev, {
        id: newId,
        name: name,
        content: 'Welcome to Google Docs Integration. Click Save to Docs to sync with your Google account!',
        docUrl: null
      }]);
      setActiveDocTabId(newId);
    } else if (promptType === 'weekly_tests') {
      const newId = `test-${Date.now()}`;
      setGoogleWeeklyTests(prev => [...prev, {
        id: newId,
        name: name,
        content: 'Welcome to Weekly Tests. Click Save to Docs to sync with your Google account!',
        docUrl: null
      }]);
      setActiveTestsTabId(newId);
    } else if (promptType === 'worksheets') {
      const newId = `worksheet-${Date.now()}`;
      setGoogleWorksheets(prev => [...prev, {
        id: newId,
        name: name,
        content: 'Welcome to Worksheets. Click Save to Docs to sync with your Google account!',
        docUrl: null
      }]);
      setActiveWorksheetsTabId(newId);
    }
    setShowPromptModal(false);
    setPromptValue('');
  };

  return (
    <div style={{
      background: 'rgba(30, 41, 59, 0.75)',
      border: '1px solid rgba(167, 139, 250, 0.4)',
      borderRadius: '16px',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      boxShadow: '0 12px 32px rgba(0,0,0,0.3)',
      color: '#fff'
    }}>
      {/* Google Sheet Modal Overlay */}
      {isSheetOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1200px',
            height: '90%',
            background: '#fff',
            borderRadius: '16px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            border: '1px solid rgba(167, 139, 250, 0.3)'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              background: '#1e293b',
              borderBottom: '1px solid #334155'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📊</span>
                <h3 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: '600' }}>Sheets</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={async () => {
                    if (isEditingTable) {
                      setIsEditingTable(false);
                      setIsSyncing(true);
                      const activeTab = timetables.find(t => t.id === activeTabId);
                      const csvData = activeTableData.map(r => `"${r.time}","${r.mon}","${r.tue}","${r.wed}","${r.thu}","${r.fri}","${r.sat}"`).join('\n');
                      const query = `SYNC_TIMETABLE_SHEET\nTitle: ${activeTab.name}\nTime,Monday,Tuesday,Wednesday,Thursday,Friday,Saturday\n${csvData}`;
                      
                      const token = localStorage.getItem('jarvis_token');
                      try {
                        const response = await fetch('/api/agent/sheets', {
                          method: 'POST',
                          headers: { 
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                          },
                          body: JSON.stringify({ query: query, session_id: 'background_task' }),
                        });
                        
                        if (response.ok) {
                          const data = await response.json();
                          const resultStr = data.result || "";
                          const urlMatch = resultStr.match(/\*\*URL:\*\* (https:\/\/docs\.google\.com\/spreadsheets\/d\/[^\s]+)/);
                          if (urlMatch) {
                            const sheetUrl = urlMatch[1];
                            setTimetables(prev => prev.map(pt => pt.id === activeTabId ? { ...pt, sheetUrl } : pt));
                          }
                          setSyncSuccess(true);
                          setTimeout(() => setSyncSuccess(false), 3000);
                        }
                      } catch (e) {
                        console.error('Failed to sync to Google Sheets', e);
                      } finally {
                        setIsSyncing(false);
                      }
                    } else {
                      setIsEditingTable(true);
                    }
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                    background: isSyncing ? '#475569' : syncSuccess ? '#10b981' : isEditingTable ? '#10b981' : '#3b82f6',
                    border: 'none', borderRadius: '8px', color: '#fff', cursor: 'pointer', transition: 'all 0.2s',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                  }}
                  onMouseOver={e => !isSyncing && !syncSuccess && (e.currentTarget.style.transform = 'translateY(-2px)')}
                  onMouseOut={e => !isSyncing && !syncSuccess && (e.currentTarget.style.transform = 'none')}
                  disabled={isSyncing}
                >
                  <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                    {isSyncing ? 'Syncing...' : syncSuccess ? 'Synced! ✅' : isEditingTable ? 'Save to Sheets' : '✏️ Edit Table'}
                  </span>
                </button>
                {timetables.find(t => t.id === activeTabId)?.sheetUrl && !isEditingTable && (
                  <button
                    onClick={() => setIsPreviewMode(!isPreviewMode)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                      background: isPreviewMode ? '#6366f1' : 'transparent',
                      border: '1px solid #6366f1', borderRadius: '8px', color: isPreviewMode ? '#fff' : '#6366f1', cursor: 'pointer', transition: 'all 0.2s',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseOut={e => e.currentTarget.style.transform = 'none'}
                  >
                    <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                      {isPreviewMode ? '🔙 Local Table' : '🌐 Preview Sheet'}
                    </span>
                  </button>
                )}
                <button 
                  onClick={() => setIsSheetOpen(false)}
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: '#e2e8f0',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    fontSize: '20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.8)'}
                  onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                >×</button>
              </div>
            </div>
            
            <div style={{
              display: 'flex', gap: '8px', padding: '12px 24px', background: '#0f172a', borderBottom: '1px solid #334155', overflowX: 'auto'
            }}>
              {timetables.map(t => (
                <button
                  key={t.id}
                  onClick={() => {
                    setActiveTabId(t.id);
                  }}
                  style={{
                    padding: '8px 16px',
                    background: activeTabId === t.id ? '#1e293b' : 'transparent',
                    border: '1px solid #334155',
                    color: activeTabId === t.id ? '#a78bfa' : '#94a3b8',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: activeTabId === t.id ? 'bold' : 'normal',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s'
                  }}
                >
                  {activeTabId === t.id ? (
                    <input 
                      value={t.name}
                      onChange={(e) => {
                        setTimetables(prev => prev.map(pt => pt.id === t.id ? { ...pt, name: e.target.value } : pt));
                      }}
                      onClick={e => e.stopPropagation()}
                      style={{
                        background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', 
                        padding: '4px', borderRadius: '4px', width: '120px', outline: 'none'
                      }}
                    />
                  ) : t.name}
                  {timetables.length > 1 && activeTabId === t.id && (
                    <span 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Are you sure you want to delete ${t.name}?`)) {
                          const newTabs = timetables.filter(pt => pt.id !== t.id);
                          setTimetables(newTabs);
                          setActiveTabId(newTabs[0].id);
                        }
                      }}
                      style={{ marginLeft: '8px', color: '#ef4444', fontSize: '14px' }}
                      title="Delete Sheet"
                    >
                      ×
                    </span>
                  )}
                </button>
              ))}
              <button 
                onClick={() => {
                  setPromptType('sheet');
                  setPromptValue(`Teacher ${timetables.length + 1}`);
                  setShowPromptModal(true);
                }}
                style={{
                  padding: '8px 16px',
                  background: 'rgba(56, 189, 248, 0.1)',
                  border: '1px dashed #38bdf8',
                  color: '#38bdf8',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s'
                }}
                onMouseOver={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.2)'}
                onMouseOut={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)'}
              >
                + Add Sheet
              </button>
            </div>
            
            <div style={{ flex: 1, position: 'relative', background: '#0f172a', padding: '24px', overflowY: 'auto' }}>
              
              {/* Lesson Plan Popup Overlay */}
              {activeLessonPlan && (
                <div style={{
                  position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                  background: 'rgba(15, 23, 42, 0.95)',
                  backdropFilter: 'blur(4px)',
                  display: 'flex', flexDirection: 'column',
                  padding: '32px', zIndex: 10,
                  overflowY: 'auto'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                    <div>
                      <h2 style={{ margin: 0, color: '#a78bfa', fontSize: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>📖</span> Lecture Plan
                      </h2>
                      <div style={{ color: '#94a3b8', fontSize: '14px', marginTop: '4px', fontWeight: 'bold' }}>
                        {activeLessonPlan.grade} • {activeLessonPlan.subject}
                      </div>
                    </div>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setActiveLessonPlan(null); }}
                      style={{
                        background: 'rgba(255,255,255,0.1)', border: 'none', color: '#e2e8f0',
                        width: '32px', height: '32px', borderRadius: '50%', fontSize: '18px', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}
                    >×</button>
                  </div>
                  
                  <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', border: '1px solid #334155', color: '#e2e8f0', lineHeight: '1.6' }}>
                    <h3 style={{ color: '#38bdf8', marginTop: 0, fontSize: '18px' }}>Topic: Advanced {activeLessonPlan.subject} Concepts</h3>
                    <p style={{ fontSize: '14px', color: '#cbd5e1' }}><strong>Objective:</strong> Students will be able to grasp core fundamentals and apply them to real-world problem-solving scenarios.</p>
                    
                    <h4 style={{ color: '#a78bfa', borderBottom: '1px solid #334155', paddingBottom: '8px', marginTop: '24px', fontSize: '15px' }}>1. Introduction (10 mins)</h4>
                    <ul style={{ paddingLeft: '20px', fontSize: '14px', color: '#94a3b8' }}>
                      <li>Warm-up exercise assessing previous knowledge.</li>
                      <li>Introduce the day's core concept using a practical real-life example.</li>
                    </ul>
                    
                    <h4 style={{ color: '#a78bfa', borderBottom: '1px solid #334155', paddingBottom: '8px', marginTop: '24px', fontSize: '15px' }}>2. Core Concept & Demonstration (20 mins)</h4>
                    <ul style={{ paddingLeft: '20px', fontSize: '14px', color: '#94a3b8' }}>
                      <li>Define key terminology and principles.</li>
                      <li>Walk through 2-3 guided examples on the interactive whiteboard.</li>
                      <li>Engage students with brief Q&A to check comprehension.</li>
                    </ul>
                    
                    <h4 style={{ color: '#a78bfa', borderBottom: '1px solid #334155', paddingBottom: '8px', marginTop: '24px', fontSize: '15px' }}>3. Independent Practice (10 mins)</h4>
                    <ul style={{ paddingLeft: '20px', fontSize: '14px', color: '#94a3b8' }}>
                      <li>Distribute practice worksheet focused on application.</li>
                      <li>Circulate the room to provide 1-on-1 assistance to students.</li>
                    </ul>
                    
                    <h4 style={{ color: '#a78bfa', borderBottom: '1px solid #334155', paddingBottom: '8px', marginTop: '24px', fontSize: '15px' }}>4. Conclusion & Homework (5 mins)</h4>
                    <ul style={{ paddingLeft: '20px', fontSize: '14px', color: '#94a3b8' }}>
                      <li>Summarize key takeaways from the lesson.</li>
                      <li>Assign relevant chapters/exercises for homework.</li>
                    </ul>
                  </div>
                  
                  <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                    <button 
                      onClick={() => {
                        setGrade(activeLessonPlan.grade);
                        setSubject(activeLessonPlan.subject);
                        setSelectedTask('lesson_plan');
                        setActiveLessonPlan(null);
                        setIsSheetOpen(false);
                      }}
                      style={{
                        padding: '10px 16px', background: '#3b82f6', border: 'none', borderRadius: '6px',
                        color: '#fff', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px',
                        transition: 'background 0.2s'
                      }}
                      onMouseOver={e => e.currentTarget.style.background = '#2563eb'}
                      onMouseOut={e => e.currentTarget.style.background = '#3b82f6'}
                    >
                      Export / Automate This Plan
                    </button>
                  </div>
                </div>
              )}

              {isPreviewMode && timetables.find(t => t.id === activeTabId)?.sheetUrl ? (
                <div style={{ width: '100%', height: '600px', borderRadius: '8px', overflow: 'hidden' }}>
                  <iframe 
                    src={`${timetables.find(t => t.id === activeTabId).sheetUrl}?rm=minimal`} 
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Google Sheets Preview"
                  />
                </div>
              ) : (
                <>
                  <table style={{ width: '100%', borderCollapse: 'collapse', color: '#e2e8f0', fontSize: '14px', textAlign: 'center' }}>
                <thead>
                  <tr>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Time</th>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Monday</th>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Tuesday</th>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Wednesday</th>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Thursday</th>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Friday</th>
                    <th style={{ border: '1px solid #334155', padding: '12px', background: '#1e293b' }}>Saturday</th>
                  </tr>
                </thead>
                <tbody>
                  {activeTableData.map((row, idx) => (
                    <tr key={idx}>
                      <td style={{ border: '1px solid #334155', padding: isEditingTable ? '4px' : '12px', fontWeight: 'bold', background: '#1e293b', whiteSpace: 'nowrap', color: '#e2e8f0' }}>
                        {isEditingTable ? (
                          <input
                            value={row.time}
                            onChange={(e) => handleTableChange(idx, 'time', e.target.value)}
                            style={{
                              width: '100px',
                              background: 'rgba(255,255,255,0.05)',
                              border: '1px solid #475569',
                              color: '#e2e8f0',
                              padding: '8px',
                              borderRadius: '4px',
                              fontSize: '13px',
                              textAlign: 'center',
                              outline: 'none',
                              fontWeight: 'bold'
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#38bdf8'}
                            onBlur={(e) => e.target.style.borderColor = '#475569'}
                          />
                        ) : row.time}
                      </td>
                      {['mon', 'tue', 'wed', 'thu', 'fri', 'sat'].map(day => {
                        const cellValue = row[day];
                        const isNonLesson = ['Break', 'Lunch', 'Free', 'Planning Period', 'Planning', 'Staff Meeting'].includes(cellValue);
                        return (
                          <td 
                            key={day} 
                            onClick={() => {
                              if (!isEditingTable) handleCellClick(cellValue);
                            }}
                            style={{ 
                              border: '1px solid #334155', 
                              padding: isEditingTable ? '4px' : '12px',
                              cursor: isEditingTable ? 'text' : (isNonLesson ? 'default' : 'pointer'),
                              color: isNonLesson ? '#64748b' : '#38bdf8',
                              transition: 'all 0.2s',
                              background: 'transparent'
                            }}
                            onMouseOver={(e) => {
                              if (!isNonLesson && !isEditingTable) {
                                e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)';
                                e.currentTarget.style.textDecoration = 'underline';
                              }
                            }}
                            onMouseOut={(e) => {
                              if (!isNonLesson && !isEditingTable) {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.textDecoration = 'none';
                              }
                            }}
                          >
                            {isEditingTable ? (
                              <input
                                value={cellValue}
                                onChange={(e) => handleTableChange(idx, day, e.target.value)}
                                style={{
                                  width: '100%',
                                  background: 'rgba(255,255,255,0.05)',
                                  border: '1px solid #475569',
                                  color: '#e2e8f0',
                                  padding: '8px',
                                  borderRadius: '4px',
                                  fontSize: '13px',
                                  textAlign: 'center',
                                  outline: 'none'
                                }}
                                onFocus={(e) => e.target.style.borderColor = '#38bdf8'}
                                onBlur={(e) => e.target.style.borderColor = '#475569'}
                              />
                            ) : cellValue}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              {isEditingTable && (
                <button
                  onClick={() => {
                    setTimetables(prev => prev.map(t => {
                      if (t.id === activeTabId) {
                        return { ...t, data: [...t.data, { time: '', mon: '', tue: '', wed: '', thu: '', fri: '', sat: '' }] };
                      }
                      return t;
                    }));
                  }}
                  style={{
                    width: '100%', padding: '12px', background: 'rgba(56, 189, 248, 0.1)', border: '1px dashed #38bdf8', 
                    color: '#38bdf8', marginTop: '16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.2)'}
                  onMouseOut={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)'}
                >
                  + Add Row
                </button>
              )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Docs Editor Modal Overlay */}
      {isDocOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 999,
          padding: '24px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1200px',
            height: '90%',
            background: '#fff',
            borderRadius: '16px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            border: '1px solid rgba(167, 139, 250, 0.3)'
          }}>
            {/* Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              background: '#1e293b',
              borderBottom: '1px solid #334155'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📝</span>
                <h3 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: '600' }}>Docs</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={async () => {
                    setIsSyncingDoc(true);
                    const activeTab = googleDocs.find(t => t.id === activeDocTabId);
                    const query = `SYNC_DOCUMENT\nTitle: ${activeTab.name}\nContent:\n${activeTab.content}`;
                    
                    const token = localStorage.getItem('jarvis_token');
                    try {
                      const response = await fetch('/api/agent/docs', {
                        method: 'POST',
                        headers: { 
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ query: query, session_id: 'background_task' }),
                      });
                      
                      if (response.ok) {
                        const data = await response.json();
                        const resultStr = data.result || "";
                        const urlMatch = resultStr.match(/\*\*URL:\*\* (https:\/\/docs\.google\.com\/document\/d\/[^\s]+)/);
                        if (urlMatch) {
                          const docUrl = urlMatch[1];
                          setGoogleDocs(prev => prev.map(pt => pt.id === activeDocTabId ? { ...pt, docUrl } : pt));
                        }
                        setSyncDocSuccess(true);
                        setTimeout(() => setSyncDocSuccess(false), 3000);
                      }
                    } catch (e) {
                      console.error('Failed to sync to Google Docs', e);
                    } finally {
                      setIsSyncingDoc(false);
                    }
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                    background: isSyncingDoc ? '#475569' : syncDocSuccess ? '#10b981' : '#3b82f6',
                    border: 'none', borderRadius: '8px', color: '#fff', cursor: 'pointer', transition: 'all 0.2s',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                  }}
                  onMouseOver={e => !isSyncingDoc && !syncDocSuccess && (e.currentTarget.style.transform = 'translateY(-2px)')}
                  onMouseOut={e => !isSyncingDoc && !syncDocSuccess && (e.currentTarget.style.transform = 'none')}
                  disabled={isSyncingDoc}
                >
                  <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                    {isSyncingDoc ? 'Syncing...' : syncDocSuccess ? 'Synced! ✅' : 'Save to Docs'}
                  </span>
                </button>

                {googleDocs.find(t => t.id === activeDocTabId)?.docUrl && (
                  <button
                    onClick={() => setIsPreviewDocMode(!isPreviewDocMode)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                      background: isPreviewDocMode ? '#6366f1' : 'transparent',
                      border: '1px solid #6366f1', borderRadius: '8px', color: isPreviewDocMode ? '#fff' : '#6366f1', cursor: 'pointer', transition: 'all 0.2s',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseOut={e => e.currentTarget.style.transform = 'none'}
                  >
                    <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                      {isPreviewDocMode ? '🔙 Local Doc' : '🌐 Preview Doc'}
                    </span>
                  </button>
                )}

                <button 
                  onClick={() => setIsDocOpen(false)}
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: '#e2e8f0',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    fontSize: '20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.8)'}
                  onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                >×</button>
              </div>
            </div>

            {/* Document Tabs */}
            <div style={{
              display: 'flex', gap: '8px', padding: '12px 24px', background: '#0f172a', borderBottom: '1px solid #334155', overflowX: 'auto'
            }}>
              {googleDocs.map(t => (
                <button
                  key={t.id}
                  onClick={() => {
                    setActiveDocTabId(t.id);
                  }}
                  style={{
                    padding: '8px 16px',
                    background: activeDocTabId === t.id ? '#1e293b' : 'transparent',
                    border: '1px solid #334155',
                    color: activeDocTabId === t.id ? '#a78bfa' : '#94a3b8',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: activeDocTabId === t.id ? 'bold' : 'normal',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s'
                  }}
                >
                  {activeDocTabId === t.id ? (
                    <input 
                      value={t.name}
                      onChange={(e) => {
                        setGoogleDocs(prev => prev.map(pt => pt.id === t.id ? { ...pt, name: e.target.value } : pt));
                      }}
                      onClick={e => e.stopPropagation()}
                      style={{
                        background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', 
                        padding: '4px', borderRadius: '4px', width: '120px', outline: 'none'
                      }}
                    />
                  ) : t.name}
                  {googleDocs.length > 1 && activeDocTabId === t.id && (
                    <span 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Are you sure you want to delete ${t.name}?`)) {
                          const newTabs = googleDocs.filter(pt => pt.id !== t.id);
                          setGoogleDocs(newTabs);
                          setActiveDocTabId(newTabs[0].id);
                        }
                      }}
                      style={{ marginLeft: '8px', color: '#ef4444', fontSize: '14px' }}
                      title="Delete Doc"
                    >
                      ×
                    </span>
                  )}
                </button>
              ))}
              <button 
                onClick={() => {
                  setPromptType('doc');
                  setPromptValue(`Doc ${googleDocs.length + 1}`);
                  setShowPromptModal(true);
                }}
                style={{
                  padding: '8px 16px',
                  background: 'rgba(56, 189, 248, 0.1)',
                  border: '1px dashed #38bdf8',
                  color: '#38bdf8',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s'
                }}
                onMouseOver={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.2)'}
                onMouseOut={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)'}
              >
                + Add Doc
              </button>
            </div>

            {/* Document Content / Preview Area */}
            <div style={{ flex: 1, position: 'relative', background: '#0f172a', padding: '24px', overflowY: 'auto' }}>
              {isPreviewDocMode && googleDocs.find(t => t.id === activeDocTabId)?.docUrl ? (
                <div style={{ width: '100%', height: '100%', borderRadius: '8px', overflow: 'hidden' }}>
                  <iframe 
                    src={`${googleDocs.find(t => t.id === activeDocTabId).docUrl}?rm=minimal`} 
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Google Docs Preview"
                  />
                </div>
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <textarea
                    value={googleDocs.find(t => t.id === activeDocTabId)?.content || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setGoogleDocs(prev => prev.map(t => t.id === activeDocTabId ? { ...t, content: val } : t));
                    }}
                    style={{
                      width: '100%',
                      flex: 1,
                      minHeight: '400px',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      padding: '16px',
                      fontSize: '15px',
                      fontFamily: 'monospace',
                      outline: 'none',
                      resize: 'none',
                      lineHeight: '1.6'
                    }}
                    placeholder="Enter document content here... Use Markdown or plain text."
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Weekly Tests Editor Modal Overlay */}
      {isTestsOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 999,
          padding: '24px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1200px',
            height: '90%',
            background: '#fff',
            borderRadius: '16px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            border: '1px solid rgba(167, 139, 250, 0.3)'
          }}>
            {/* Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              background: '#1e293b',
              borderBottom: '1px solid #334155'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>⚡</span>
                <h3 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: '600' }}>Weekly Tests</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={async () => {
                    setIsSyncingTests(true);
                    const activeTab = googleWeeklyTests.find(t => t.id === activeTestsTabId);
                    const query = `SYNC_DOCUMENT\nTitle: ${activeTab.name}\nContent:\n${activeTab.content}`;
                    
                    const token = localStorage.getItem('jarvis_token');
                    try {
                      const response = await fetch('/api/agent/docs', {
                        method: 'POST',
                        headers: { 
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ query: query, session_id: 'background_task' }),
                      });
                      
                      if (response.ok) {
                        const data = await response.json();
                        const resultStr = data.result || "";
                        const urlMatch = resultStr.match(/\*\*URL:\*\* (https:\/\/docs\.google\.com\/document\/d\/[^\s]+)/);
                        if (urlMatch) {
                          const docUrl = urlMatch[1];
                          setGoogleWeeklyTests(prev => prev.map(pt => pt.id === activeTestsTabId ? { ...pt, docUrl } : pt));
                        }
                        setSyncTestsSuccess(true);
                        setTimeout(() => setSyncTestsSuccess(false), 3000);
                      }
                    } catch (e) {
                      console.error('Failed to sync Weekly Test', e);
                    } finally {
                      setIsSyncingTests(false);
                    }
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                    background: isSyncingTests ? '#475569' : syncTestsSuccess ? '#10b981' : '#3b82f6',
                    border: 'none', borderRadius: '8px', color: '#fff', cursor: 'pointer', transition: 'all 0.2s',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                  }}
                  onMouseOver={e => !isSyncingTests && !syncTestsSuccess && (e.currentTarget.style.transform = 'translateY(-2px)')}
                  onMouseOut={e => !isSyncingTests && !syncTestsSuccess && (e.currentTarget.style.transform = 'none')}
                  disabled={isSyncingTests}
                >
                  <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                    {isSyncingTests ? 'Syncing...' : syncTestsSuccess ? 'Synced! ✅' : 'Save to Docs'}
                  </span>
                </button>

                {googleWeeklyTests.find(t => t.id === activeTestsTabId)?.docUrl && (
                  <button
                    onClick={() => setIsPreviewTestsMode(!isPreviewTestsMode)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                      background: isPreviewTestsMode ? '#6366f1' : 'transparent',
                      border: '1px solid #6366f1', borderRadius: '8px', color: isPreviewTestsMode ? '#fff' : '#6366f1', cursor: 'pointer', transition: 'all 0.2s',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseOut={e => e.currentTarget.style.transform = 'none'}
                  >
                    <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                      {isPreviewTestsMode ? '🔙 Local Doc' : '🌐 Preview Doc'}
                    </span>
                  </button>
                )}

                <button 
                  onClick={() => setIsTestsOpen(false)}
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: '#e2e8f0',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    fontSize: '20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.8)'}
                  onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                >×</button>
              </div>
            </div>

            {/* Document Tabs */}
            <div style={{
              display: 'flex', gap: '8px', padding: '12px 24px', background: '#0f172a', borderBottom: '1px solid #334155', overflowX: 'auto'
            }}>
              {googleWeeklyTests.map(t => (
                <button
                  key={t.id}
                  onClick={() => {
                    setActiveTestsTabId(t.id);
                  }}
                  style={{
                    padding: '8px 16px',
                    background: activeTestsTabId === t.id ? '#1e293b' : 'transparent',
                    border: '1px solid #334155',
                    color: activeTestsTabId === t.id ? '#a78bfa' : '#94a3b8',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: activeTestsTabId === t.id ? 'bold' : 'normal',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s'
                  }}
                >
                  {activeTestsTabId === t.id ? (
                    <input 
                      value={t.name}
                      onChange={(e) => {
                        setGoogleWeeklyTests(prev => prev.map(pt => pt.id === t.id ? { ...pt, name: e.target.value } : pt));
                      }}
                      onClick={e => e.stopPropagation()}
                      style={{
                        background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', 
                        padding: '4px', borderRadius: '4px', width: '120px', outline: 'none'
                      }}
                    />
                  ) : t.name}
                  {googleWeeklyTests.length > 1 && activeTestsTabId === t.id && (
                    <span 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Are you sure you want to delete ${t.name}?`)) {
                          const newTabs = googleWeeklyTests.filter(pt => pt.id !== t.id);
                          setGoogleWeeklyTests(newTabs);
                          setActiveTestsTabId(newTabs[0].id);
                        }
                      }}
                      style={{ marginLeft: '8px', color: '#ef4444', fontSize: '14px' }}
                      title="Delete Doc"
                    >
                      ×
                    </span>
                  )}
                </button>
              ))}
              <button 
                onClick={() => {
                  setPromptType('weekly_tests');
                  setPromptValue(`Weekly Test ${googleWeeklyTests.length + 1}`);
                  setShowPromptModal(true);
                }}
                style={{
                  padding: '8px 16px',
                  background: 'rgba(56, 189, 248, 0.1)',
                  border: '1px dashed #38bdf8',
                  color: '#38bdf8',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s'
                }}
                onMouseOver={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.2)'}
                onMouseOut={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)'}
              >
                + Add Doc
              </button>
            </div>

            {/* Document Content / Preview Area */}
            <div style={{ flex: 1, position: 'relative', background: '#0f172a', padding: '24px', overflowY: 'auto' }}>
              {isPreviewTestsMode && googleWeeklyTests.find(t => t.id === activeTestsTabId)?.docUrl ? (
                <div style={{ width: '100%', height: '100%', borderRadius: '8px', overflow: 'hidden' }}>
                  <iframe 
                    src={`${googleWeeklyTests.find(t => t.id === activeTestsTabId).docUrl}?rm=minimal`} 
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Google Docs Preview"
                  />
                </div>
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <textarea
                    value={googleWeeklyTests.find(t => t.id === activeTestsTabId)?.content || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setGoogleWeeklyTests(prev => prev.map(t => t.id === activeTestsTabId ? { ...t, content: val } : t));
                    }}
                    style={{
                      width: '100%',
                      flex: 1,
                      minHeight: '400px',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      padding: '16px',
                      fontSize: '15px',
                      fontFamily: 'monospace',
                      outline: 'none',
                      resize: 'none',
                      lineHeight: '1.6'
                    }}
                    placeholder="Enter weekly test contents here..."
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Worksheets Editor Modal Overlay */}
      {isWorksheetsOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 999,
          padding: '24px'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '1200px',
            height: '90%',
            background: '#fff',
            borderRadius: '16px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            border: '1px solid rgba(167, 139, 250, 0.3)'
          }}>
            {/* Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              background: '#1e293b',
              borderBottom: '1px solid #334155'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📝</span>
                <h3 style={{ margin: 0, color: '#fff', fontSize: '18px', fontWeight: '600' }}>Worksheets</h3>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={async () => {
                    setIsSyncingWorksheets(true);
                    const activeTab = googleWorksheets.find(t => t.id === activeWorksheetsTabId);
                    const query = `SYNC_DOCUMENT\nTitle: ${activeTab.name}\nContent:\n${activeTab.content}`;
                    
                    const token = localStorage.getItem('jarvis_token');
                    try {
                      const response = await fetch('/api/agent/docs', {
                        method: 'POST',
                        headers: { 
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({ query: query, session_id: 'background_task' }),
                      });
                      
                      if (response.ok) {
                        const data = await response.json();
                        const resultStr = data.result || "";
                        const urlMatch = resultStr.match(/\*\*URL:\*\* (https:\/\/docs\.google\.com\/document\/d\/[^\s]+)/);
                        if (urlMatch) {
                          const docUrl = urlMatch[1];
                          setGoogleWorksheets(prev => prev.map(pt => pt.id === activeWorksheetsTabId ? { ...pt, docUrl } : pt));
                        }
                        setSyncWorksheetsSuccess(true);
                        setTimeout(() => setSyncWorksheetsSuccess(false), 3000);
                      }
                    } catch (e) {
                      console.error('Failed to sync Worksheet', e);
                    } finally {
                      setIsSyncingWorksheets(false);
                    }
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                    background: isSyncingWorksheets ? '#475569' : syncWorksheetsSuccess ? '#10b981' : '#3b82f6',
                    border: 'none', borderRadius: '8px', color: '#fff', cursor: 'pointer', transition: 'all 0.2s',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                  }}
                  onMouseOver={e => !isSyncingWorksheets && !syncWorksheetsSuccess && (e.currentTarget.style.transform = 'translateY(-2px)')}
                  onMouseOut={e => !isSyncingWorksheets && !syncWorksheetsSuccess && (e.currentTarget.style.transform = 'none')}
                  disabled={isSyncingWorksheets}
                >
                  <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                    {isSyncingWorksheets ? 'Syncing...' : syncWorksheetsSuccess ? 'Synced! ✅' : 'Save to Docs'}
                  </span>
                </button>

                {googleWorksheets.find(t => t.id === activeWorksheetsTabId)?.docUrl && (
                  <button
                    onClick={() => setIsPreviewWorksheetsMode(!isPreviewWorksheetsMode)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                      background: isPreviewWorksheetsMode ? '#6366f1' : 'transparent',
                      border: '1px solid #6366f1', borderRadius: '8px', color: isPreviewWorksheetsMode ? '#fff' : '#6366f1', cursor: 'pointer', transition: 'all 0.2s',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                    }}
                    onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseOut={e => e.currentTarget.style.transform = 'none'}
                  >
                    <span style={{ fontSize: '13px', fontWeight: 'bold' }}>
                      {isPreviewWorksheetsMode ? '🔙 Local Doc' : '🌐 Preview Doc'}
                    </span>
                  </button>
                )}

                <button 
                  onClick={() => setIsWorksheetsOpen(false)}
                  style={{
                    background: 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: '#e2e8f0',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    fontSize: '20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.8)'}
                  onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                >×</button>
              </div>
            </div>

            {/* Document Tabs */}
            <div style={{
              display: 'flex', gap: '8px', padding: '12px 24px', background: '#0f172a', borderBottom: '1px solid #334155', overflowX: 'auto'
            }}>
              {googleWorksheets.map(t => (
                <button
                  key={t.id}
                  onClick={() => {
                    setActiveWorksheetsTabId(t.id);
                  }}
                  style={{
                    padding: '8px 16px',
                    background: activeWorksheetsTabId === t.id ? '#1e293b' : 'transparent',
                    border: '1px solid #334155',
                    color: activeWorksheetsTabId === t.id ? '#a78bfa' : '#94a3b8',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: activeWorksheetsTabId === t.id ? 'bold' : 'normal',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s'
                  }}
                >
                  {activeWorksheetsTabId === t.id ? (
                    <input 
                      value={t.name}
                      onChange={(e) => {
                        setGoogleWorksheets(prev => prev.map(pt => pt.id === t.id ? { ...pt, name: e.target.value } : pt));
                      }}
                      onClick={e => e.stopPropagation()}
                      style={{
                        background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', 
                        padding: '4px', borderRadius: '4px', width: '120px', outline: 'none'
                      }}
                    />
                  ) : t.name}
                  {googleWorksheets.length > 1 && activeWorksheetsTabId === t.id && (
                    <span 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Are you sure you want to delete ${t.name}?`)) {
                          const newTabs = googleWorksheets.filter(pt => pt.id !== t.id);
                          setGoogleWorksheets(newTabs);
                          setActiveWorksheetsTabId(newTabs[0].id);
                        }
                      }}
                      style={{ marginLeft: '8px', color: '#ef4444', fontSize: '14px' }}
                      title="Delete Doc"
                    >
                      ×
                    </span>
                  )}
                </button>
              ))}
              <button 
                onClick={() => {
                  setPromptType('worksheets');
                  setPromptValue(`Worksheet ${googleWorksheets.length + 1}`);
                  setShowPromptModal(true);
                }}
                style={{
                  padding: '8px 16px',
                  background: 'rgba(56, 189, 248, 0.1)',
                  border: '1px dashed #38bdf8',
                  color: '#38bdf8',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s'
                }}
                onMouseOver={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.2)'}
                onMouseOut={e => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.1)'}
              >
                + Add Doc
              </button>
            </div>

            {/* Document Content / Preview Area */}
            <div style={{ flex: 1, position: 'relative', background: '#0f172a', padding: '24px', overflowY: 'auto' }}>
              {isPreviewWorksheetsMode && googleWorksheets.find(t => t.id === activeWorksheetsTabId)?.docUrl ? (
                <div style={{ width: '100%', height: '100%', borderRadius: '8px', overflow: 'hidden' }}>
                  <iframe 
                    src={`${googleWorksheets.find(t => t.id === activeWorksheetsTabId).docUrl}?rm=minimal`} 
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Google Docs Preview"
                  />
                </div>
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <textarea
                    value={googleWorksheets.find(t => t.id === activeWorksheetsTabId)?.content || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setGoogleWorksheets(prev => prev.map(t => t.id === activeWorksheetsTabId ? { ...t, content: val } : t));
                    }}
                    style={{
                      width: '100%',
                      flex: 1,
                      minHeight: '400px',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      padding: '16px',
                      fontSize: '15px',
                      fontFamily: 'monospace',
                      outline: 'none',
                      resize: 'none',
                      lineHeight: '1.6'
                    }}
                    placeholder="Enter worksheet contents here..."
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <h2 style={{ margin: 0, fontSize: '22px', color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '10px' }}>
          🏫 Unified Teacher Workstation
        </h2>
        <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
          Automate your daily school tasks using Google Workspace and Advanced RAG.
        </p>
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
        gap: '24px',
        marginTop: '24px'
      }}>
        {tasks.map(t => (
          <div
            key={t.id}
            onClick={() => {
              if (t.id === 'timetable') {
                setIsSheetOpen(true);
              } else if (t.id === 'docs') {
                setIsDocOpen(true);
              } else if (t.id === 'weekly_tests') {
                setIsTestsOpen(true);
              } else if (t.id === 'worksheets') {
                setIsWorksheetsOpen(true);
              }
            }}
            style={{
              background: 'rgba(30, 41, 59, 0.4)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '16px',
              padding: '32px 24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '16px',
              cursor: 'pointer',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              textAlign: 'center',
              boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
            }}
            onMouseOver={e => {
              e.currentTarget.style.transform = 'translateY(-4px)';
              e.currentTarget.style.borderColor = 'rgba(167, 139, 250, 0.4)';
              e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
            }}
            onMouseOut={e => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
              e.currentTarget.style.background = 'rgba(30, 41, 59, 0.4)';
            }}
          >
            <span style={{ fontSize: '48px', filter: 'drop-shadow(0 0 10px rgba(167, 139, 250, 0.3))' }}>{t.emoji}</span>
            <div>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: 'bold', color: '#fff' }}>{t.name}</h3>
              <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8', lineHeight: '1.5' }}>{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

          {/* Custom Prompt Modal */}
          {showPromptModal && (
            <div style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(15, 23, 42, 0.85)',
              backdropFilter: 'blur(8px)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              zIndex: 10000,
              padding: '24px'
            }}>
              <div style={{
                width: '100%',
                maxWidth: '400px',
                background: '#1e293b',
                borderRadius: '12px',
                border: '1px solid rgba(167, 139, 250, 0.3)',
                padding: '24px',
                boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}>
                <h4 style={{ margin: 0, color: '#fff', fontSize: '16px', fontWeight: 'bold' }}>
                  {promptType === 'sheet' ? 'Name Your Sheet' : 'Name Your Document'}
                </h4>
                <input
                  autoFocus
                  value={promptValue}
                  onChange={(e) => setPromptValue(e.target.value)}
                  placeholder={promptType === 'sheet' ? "Enter sheet name..." : "Enter document name..."}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handlePromptConfirm();
                    }
                  }}
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid #475569',
                    color: '#fff',
                    padding: '10px',
                    borderRadius: '8px',
                    outline: 'none',
                    fontSize: '14px'
                  }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button
                    onClick={() => {
                      setShowPromptModal(false);
                      setPromptValue('');
                    }}
                    style={{
                      background: 'transparent',
                      border: '1px solid #475569',
                      color: '#94a3b8',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '13px'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handlePromptConfirm}
                    style={{
                      background: '#38bdf8',
                      border: 'none',
                      color: '#0f172a',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      fontSize: '13px'
                    }}
                  >
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      );
    }
