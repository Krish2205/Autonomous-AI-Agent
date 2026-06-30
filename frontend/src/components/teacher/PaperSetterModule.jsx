import React, { useState } from 'react';

export default function PaperSetterModule({ onSend, isLoading, onUpload, isUploading }) {
  const [course, setCourse] = useState('Mathematics');
  const [grade, setGrade] = useState('Class 10');
  const [totalMarks, setTotalMarks] = useState('50 Marks');
  const [board, setBoard] = useState('CBSE');
  const [bloomLevel, setBloomLevel] = useState('Application');
  const [uploadedReference, setUploadedReference] = useState('');
  const [questionTypes, setQuestionTypes] = useState({
    competency: true,
    mcq: true,
    assertionReason: true,
    caseStudy: false,
    shortAnswer: true,
    longAnswer: false
  });

  const toggleType = (type) => {
    setQuestionTypes(prev => ({ ...prev, [type]: !prev[type] }));
  };

  const handleReferenceChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadedReference(file.name);
    if (onUpload) {
      await onUpload(file);
    }
  };

  const handleGeneratePaper = () => {
    if (!uploadedReference) {
      alert("Please upload a reference syllabus or textbook document to ground the paper setting.");
      return;
    }
    const activeTypes = Object.entries(questionTypes)
      .filter(([_, checked]) => checked)
      .map(([name]) => name)
      .join(', ');

    onSend(`Using RAG, generate an official print-ready exam paper for ${grade} ${course} aligned with ${board} blueprint standards. Total marks: ${totalMarks}. Bloom's Focus: ${bloomLevel}. Include question formats: [${activeTypes}]. Base all questions STRICTLY on the contents of the uploaded reference document "${uploadedReference}" and output as Google Doc schema.`);
  };

  const handleDeployQuiz = () => {
    if (!uploadedReference) {
      alert("Please upload a reference syllabus or textbook document to ground the pop-quiz.");
      return;
    }
    onSend(`Using RAG, generate and deploy an online rapid quiz for ${grade} ${course} based STRICTLY on the uploaded reference document "${uploadedReference}" to Google Forms. Set active auto-grading rules with 10 questions covering core concepts.`);
  };

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.75)', border: '1px solid rgba(251, 191, 36, 0.4)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', boxShadow: '0 12px 32px rgba(0,0,0,0.3)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '16px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '22px', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '10px' }}>
            ⚡ Paper Setter & Activity Designer (RAG Grounded)
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Core GenAI Engine. Upload reference files and generate board-standard question papers and quizzes strictly grounded on the content.
          </p>
        </div>
      </div>

      {/* RAG Reference Upload Section */}
      <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(251, 191, 36, 0.2)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <label style={{ fontSize: '13px', color: '#fbbf24', fontWeight: 'bold' }}>📖 Grounding Source (RAG Reference Document):</label>
        <div style={{
          border: '2px dashed rgba(251, 191, 36, 0.4)',
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
          <span style={{ fontSize: '26px' }}>📚</span>
          <div style={{ fontSize: '12px', color: '#cbd5e1', wordBreak: 'break-all' }}>
            {isUploading ? "Uploading reference document..." : uploadedReference ? `Grounded Source: ${uploadedReference}` : "Drag & drop reference PDF, Word, or textbook file here"}
          </div>
          <input
            type="file"
            accept=".pdf,.txt,.docx"
            onChange={handleReferenceChange}
            style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              opacity: 0,
              cursor: 'pointer'
            }}
          />
          {!isUploading && !uploadedReference && (
            <span style={{ padding: '4px 12px', borderRadius: '6px', background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24', fontSize: '11px', border: '1px solid rgba(251, 191, 36, 0.3)', pointerEvents: 'none' }}>
              Select Grounding File
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Left Specs */}
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(251, 191, 36, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <h3 style={{ margin: 0, fontSize: '15px', color: '#fbbf24' }}>📋 Blueprint Roster Specs</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#cbd5e1' }}>Subject / Course:</label>
              <input type="text" value={course} onChange={e => setCourse(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '4px', borderRadius: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#cbd5e1' }}>Grade / Class:</label>
              <input type="text" value={grade} onChange={e => setGrade(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '4px', borderRadius: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '13px' }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#cbd5e1' }}>Board Affiliation:</label>
              <select value={board} onChange={e => setBoard(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '4px', borderRadius: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '13px' }}>
                <option value="CBSE">CBSE (India)</option>
                <option value="ICSE">ICSE (India)</option>
                <option value="State Board">State Board</option>
                <option value="IB">IB / Cambridge</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#cbd5e1' }}>Total Marks:</label>
              <input type="text" value={totalMarks} onChange={e => setTotalMarks(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '4px', borderRadius: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '13px' }} />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: '#cbd5e1' }}>Bloom's Taxonomy Focus:</label>
            <select value={bloomLevel} onChange={e => setBloomLevel(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '4px', borderRadius: '6px', background: '#1e293b', border: '1px solid #475569', color: '#fff', fontSize: '13px' }}>
              <option value="Knowledge">Remembering / Knowledge</option>
              <option value="Understanding">Understanding</option>
              <option value="Application">Application / Problem Solving</option>
              <option value="Analysis">Analysis & Reasoning</option>
              <option value="Evaluation">Critical Evaluation</option>
              <option value="Creation">Creation / Synthesis</option>
            </select>
          </div>
        </div>

        {/* Right Specs */}
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(251, 191, 36, 0.15)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <h3 style={{ margin: 0, fontSize: '15px', color: '#fbbf24' }}>⚙️ Question Layout Checklist</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            {Object.keys(questionTypes).map((type) => (
              <label key={type} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#cbd5e1', cursor: 'pointer' }}>
                <input type="checkbox" checked={questionTypes[type]} onChange={() => toggleType(type)} style={{ cursor: 'pointer' }} />
                <span style={{ textTransform: 'capitalize' }}>{type.replace(/([A-Z])/g, ' $1')}</span>
              </label>
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 'auto' }}>
            <button
              onClick={handleGeneratePaper}
              disabled={isLoading || isUploading || !uploadedReference}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                background: uploadedReference ? '#fbbf24' : 'rgba(251, 191, 36, 0.3)',
                color: uploadedReference ? '#0f172a' : '#64748b',
                border: 'none',
                fontWeight: '700',
                fontSize: '13px',
                cursor: uploadedReference ? 'pointer' : 'not-allowed',
                boxShadow: uploadedReference ? '0 4px 15px rgba(251, 191, 36, 0.3)' : 'none'
              }}
            >
              {uploadedReference ? "📄 Generate grounded Question Paper (Google Docs)" : "⚠️ Please upload reference file first"}
            </button>
            <button
              onClick={handleDeployQuiz}
              disabled={isLoading || isUploading || !uploadedReference}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: uploadedReference ? '#fff' : '#64748b',
                fontWeight: '600',
                fontSize: '13px',
                cursor: uploadedReference ? 'pointer' : 'not-allowed'
              }}
            >
              📊 Deploy grounded Pop-Quiz directly (Google Forms)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
