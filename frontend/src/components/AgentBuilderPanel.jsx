import { useState, useEffect, useRef } from 'react';

export default function AgentBuilderPanel({ sessionToken, onClose, onAgentReloaded }) {
  const [activeTab, setActiveTab] = useState('build');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Tab 1: Build State
  const [buildPrompt, setBuildPrompt] = useState('');
  const [buildConsole, setBuildConsole] = useState('');
  const consoleEndRef = useRef(null);

  // Tab 2: Edit State
  const [agentFiles, setAgentFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [code, setCode] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState('');

  // Fetch agent files metadata
  const fetchAgentFiles = async () => {
    if (!sessionToken) return;
    try {
      const res = await fetch('/api/agents/code', {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAgentFiles(data);
        if (data.length > 0 && !selectedFile) {
          // Default to first editable or dynamic agent if possible
          const firstDynamic = data.find(f => f.is_dynamic);
          setSelectedFile(firstDynamic ? firstDynamic.filename : data[0].filename);
        }
      }
    } catch (err) {
      console.error("Failed to list agent files:", err);
      setErrorMsg("Failed to list agent files from backend.");
    }
  };

  // Fetch code of selected agent
  const fetchAgentCode = async (filename) => {
    if (!filename || !sessionToken) return;
    setIsLoading(true);
    setValidationErrors('');
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await fetch(`/api/agents/code/${filename}`, {
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCode(data.code);
      } else {
        const err = await res.json();
        setErrorMsg(err.detail || "Failed to load agent code.");
      }
    } catch (err) {
      setErrorMsg("Failed to read agent source code.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgentFiles();
  }, [sessionToken]);

  useEffect(() => {
    if (selectedFile) {
      fetchAgentCode(selectedFile);
    }
  }, [selectedFile]);

  // Scroll build console to bottom on updates
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [buildConsole]);

  // Trigger building agent via Prompt
  const handleBuildAgent = async (e) => {
    e.preventDefault();
    if (!buildPrompt.trim()) return;

    setIsLoading(true);
    setErrorMsg('');
    setSuccessMsg('');
    setBuildConsole(`[BUILD STARTED] Sending blueprint prompt to JARVIS Agent Builder Agent...\n`);
    
    try {
      const res = await fetch('/api/agents/build', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ prompt: buildPrompt.trim() })
      });

      const data = await res.json();
      if (res.ok) {
        setBuildConsole(prev => prev + `[SUCCESS] Build task completed.\n\n--- BUILD LOGS ---\n${data.result}\n`);
        setSuccessMsg("Custom agent successfully built, compiled, and dynamically hot-reloaded!");
        setBuildPrompt('');
        fetchAgentFiles();
        if (onAgentReloaded) onAgentReloaded();
      } else {
        setBuildConsole(prev => prev + `[ERROR] Build validation check failed:\n${data.detail || 'Unknown error'}\n`);
        setErrorMsg(data.detail || "Failed to build custom agent.");
      }
    } catch (err) {
      setBuildConsole(prev => prev + `[FATAL] Network error during build request.\n`);
      setErrorMsg("Error communicating with backend.");
    } finally {
      setIsLoading(false);
    }
  };

  // Trigger saving / validating edited agent code
  const handleSaveCode = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsSaving(true);
    setErrorMsg('');
    setSuccessMsg('');
    setValidationErrors('');

    try {
      const res = await fetch(`/api/agents/code/${selectedFile}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ code })
      });

      const data = await res.json();
      if (res.ok) {
        setSuccessMsg(`Source file '${selectedFile}' compiled, tested, and registered successfully!`);
        fetchAgentFiles();
        if (onAgentReloaded) onAgentReloaded();
      } else {
        setValidationErrors(data.detail || "Validation check failed.");
        setErrorMsg("Failed to compile or import the written code. Reverted changes.");
      }
    } catch (err) {
      setErrorMsg("Failed to save changes. Network error.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="builder-overlay">
      <style>{`
        .builder-overlay {
          position: fixed;
          inset: 0;
          z-index: 900;
          background: rgba(4, 4, 12, 0.7);
          backdrop-filter: blur(15px);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #e8eaff;
          font-family: 'Inter', system-ui, sans-serif;
        }

        .builder-card {
          width: 900px;
          height: 700px;
          background: rgba(12, 12, 35, 0.75);
          border: 1px solid rgba(100, 120, 255, 0.15);
          border-radius: 20px;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(139, 92, 246, 0.05);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          position: relative;
        }

        .builder-header {
          padding: 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .builder-title-area {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .builder-icon {
          font-size: 1.6rem;
        }

        .builder-title {
          font-size: 1.25rem;
          font-weight: 800;
          letter-spacing: 2px;
          background: linear-gradient(135deg, #a78bfa, #8b5cf6, #ec4899);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .builder-close-btn {
          background: none;
          border: none;
          color: #8b8fad;
          font-size: 1.5rem;
          cursor: pointer;
          transition: color 0.2s;
        }

        .builder-close-btn:hover {
          color: #ec4899;
        }

        .builder-nav {
          display: flex;
          padding: 0 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          gap: 24px;
          background: rgba(0, 0, 0, 0.15);
        }

        .nav-tab {
          padding: 16px 8px;
          font-size: 0.85rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #8b8fad;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          transition: all 0.2s;
        }

        .nav-tab.active {
          color: #a78bfa;
          border-bottom-color: #a78bfa;
        }

        .builder-body {
          flex: 1;
          padding: 24px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .builder-alert {
          padding: 12px 16px;
          border-radius: 8px;
          font-size: 0.85rem;
          line-height: 1.4;
        }

        .builder-alert.error {
          background: rgba(244, 63, 94, 0.1);
          border: 1px solid rgba(244, 63, 94, 0.2);
          color: #f43f5e;
        }

        .builder-alert.success {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.2);
          color: #10b981;
        }

        .prompt-section {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .prompt-textarea {
          width: 100%;
          min-height: 100px;
          padding: 12px;
          background: rgba(0, 0, 0, 0.3);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          color: white;
          font-size: 0.9rem;
          outline: none;
          resize: vertical;
          font-family: inherit;
        }

        .prompt-textarea:focus {
          border-color: #a78bfa;
        }

        .console-area {
          flex: 1;
          background: rgba(5, 5, 15, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 10px;
          padding: 16px;
          font-family: 'Fira Code', monospace;
          font-size: 0.8rem;
          color: #34d399;
          overflow-y: auto;
          white-space: pre-wrap;
          max-height: 250px;
          box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        }

        .build-btn {
          align-self: flex-end;
          padding: 10px 24px;
          background: linear-gradient(135deg, #8b5cf6, #ec4899);
          border: none;
          color: white;
          border-radius: 8px;
          font-weight: 700;
          font-size: 0.85rem;
          cursor: pointer;
          transition: opacity 0.2s;
        }

        .build-btn:hover:not(:disabled) {
          opacity: 0.9;
        }

        .build-btn:disabled {
          background: #3e3f4e;
          cursor: not-allowed;
          color: #72748b;
        }

        .editor-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
        }

        .select-wrapper {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .editor-select {
          padding: 8px 16px;
          background: rgba(0, 0, 0, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #e8eaff;
          border-radius: 8px;
          font-size: 0.85rem;
          outline: none;
        }

        .editor-textarea {
          width: 100%;
          flex: 1;
          min-height: 300px;
          padding: 16px;
          background: rgba(5, 5, 12, 0.65);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          color: #38bdf8;
          font-family: 'Fira Code', 'Courier New', monospace;
          font-size: 0.85rem;
          line-height: 1.5;
          outline: none;
          resize: none;
        }

        .editor-textarea:focus {
          border-color: #a78bfa;
          box-shadow: 0 0 10px rgba(139, 92, 246, 0.1);
        }

        .dynamic-badge {
          padding: 2px 8px;
          font-size: 0.65rem;
          background: rgba(16, 185, 129, 0.15);
          color: #34d399;
          border: 1px solid rgba(16, 185, 129, 0.3);
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: 700;
        }

        .static-badge {
          padding: 2px 8px;
          font-size: 0.65rem;
          background: rgba(255, 255, 255, 0.05);
          color: #8b8fad;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: 700;
        }

        .error-traceback {
          background: rgba(244, 63, 94, 0.05);
          border: 1px solid rgba(244, 63, 94, 0.2);
          color: #f43f5e;
          padding: 12px;
          border-radius: 8px;
          font-family: monospace;
          font-size: 0.75rem;
          white-space: pre-wrap;
          overflow-y: auto;
          max-height: 120px;
        }
      `}</style>

      <div className="builder-card">
        <div className="builder-header">
          <div className="builder-title-area">
            <span className="builder-icon">🤖</span>
            <h3 className="builder-title">Meta-Agent Builder OS Control Panel</h3>
          </div>
          <button className="builder-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="builder-nav">
          <button
            className={`nav-tab ${activeTab === 'build' ? 'active' : ''}`}
            onClick={() => setActiveTab('build')}
          >
            Create Agent
          </button>
          <button
            className={`nav-tab ${activeTab === 'edit' ? 'active' : ''}`}
            onClick={() => setActiveTab('edit')}
          >
            Edit Source Code
          </button>
        </div>

        <div className="builder-body">
          {errorMsg && <div className="builder-alert error">{errorMsg}</div>}
          {successMsg && <div className="builder-alert success">{successMsg}</div>}

          {activeTab === 'build' ? (
            <>
              <div className="prompt-section">
                <label style={{ fontSize: '0.8rem', color: '#8b8fad', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 'bold' }}>Describe the Custom Agent</label>
                <textarea
                  className="prompt-textarea"
                  placeholder="Describe what the agent should do. E.g. 'Create a weather agent named weather_test that queries Tavily Search for current weather conditions in a city and returns a friendly formatted update.'"
                  value={buildPrompt}
                  onChange={(e) => setBuildPrompt(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              <button
                className="build-btn"
                onClick={handleBuildAgent}
                disabled={isLoading || !buildPrompt.trim()}
              >
                {isLoading ? 'Building Agent...' : 'Generate and Hot-Reload Agent'}
              </button>

              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: '#8b8fad', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Build Terminal</span>
                <div className="console-area">
                  {buildConsole || '[OFFLINE] Awaiting build trigger...'}
                  <div ref={consoleEndRef} />
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="editor-header">
                <div className="select-wrapper">
                  <span style={{ fontSize: '0.8rem', color: '#8b8fad', fontWeight: 'bold' }}>Agent File:</span>
                  <select
                    className="editor-select"
                    value={selectedFile}
                    onChange={(e) => setSelectedFile(e.target.value)}
                    disabled={isLoading || isSaving}
                  >
                    {agentFiles.map((file) => (
                      <option key={file.filename} value={file.filename}>
                        {file.filename} ({file.name})
                      </option>
                    ))}
                  </select>
                </div>
                {selectedFile && (
                  <div>
                    {agentFiles.find(f => f.filename === selectedFile)?.is_dynamic ? (
                      <span className="dynamic-badge">Dynamic Custom Agent</span>
                    ) : (
                      <span className="static-badge">Core System Agent</span>
                    )}
                  </div>
                )}
              </div>

              {validationErrors && (
                <div className="error-traceback">
                  <strong>Compilation Failure Traceback:</strong>
                  <p>{validationErrors}</p>
                </div>
              )}

              {isLoading ? (
                <div style={{ color: '#00d4ff', fontSize: '0.9rem', textAlign: 'center', margin: '40px' }}>Loading source code...</div>
              ) : (
                <textarea
                  className="editor-textarea"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  disabled={isSaving}
                  spellCheck="false"
                />
              )}

              <button
                className="build-btn"
                onClick={handleSaveCode}
                disabled={isSaving || isLoading || !selectedFile}
              >
                {isSaving ? 'Compiling & Validating...' : 'Compile, Save & Reload'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
