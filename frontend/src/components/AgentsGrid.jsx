import { useState, useEffect, useRef } from 'react';

const AGENT_ICONS = {
  search: { icon: '🔍' },
  code: { icon: '💻' },
  analyse: { icon: '📊' },
  summary: { icon: '📝' },
  email: { icon: '📧' },
  database: { icon: '🗄️' },
  scraper: { icon: '🌐' },
  agent_builder: { icon: '🔧' },
  calendar: { icon: '📅' },
  devops: { icon: '⚙️' },
  finance: { icon: '💵' },
  image_gen: { icon: '🎨' },
  maps: { icon: '🗺️' },
  notification: { icon: '🔔' },
  package_manager: { icon: '📦' },
  translation: { icon: '🗣️' },
  video_to_mp3: { icon: '🎬' },
  visualization: { icon: '📈' },
  voice: { icon: '🎙️' },
  dev_team: { icon: '👥' },
  analyst_team: { icon: '🔎' },
  ops_team: { icon: '🏢' }
};

export default function AgentsGrid({ activeAgents = [], sessionToken, onToast }) {
  const [agents, setAgents] = useState([]);
  const [enabledAgents, setEnabledAgents] = useState([]);
  const [agentConfigs, setAgentConfigs] = useState({});
  const [customAgents, setCustomAgents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Drawer States
  const [isEditing, setIsEditing] = useState(null); // agent name or null
  const [isCreating, setIsCreating] = useState(false);

  // Edit Form States
  const [editPrompt, setEditPrompt] = useState("");
  const [editModel, setEditModel] = useState("llama-3.3-70b-versatile");
  const [editTemp, setEditTemp] = useState(0.3);
  const [isSavingConfig, setIsSavingConfig] = useState(false);

  // Custom Agent Form States
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPrompt, setNewPrompt] = useState("");
  const [newModel, setNewModel] = useState("llama-3.3-70b-versatile");
  const [newTemp, setNewTemp] = useState(0.3);
  const [newBaseAgent, setNewBaseAgent] = useState("");
  const [isCreatingAgent, setIsCreatingAgent] = useState(false);

  // Sandbox Test Shell States
  const [testQuery, setTestQuery] = useState("");
  const [testResult, setTestResult] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const consoleEndRef = useRef(null);

  const fetchWorkspaceAgents = async () => {
    setIsLoading(true);
    try {
      const headers = {};
      if (sessionToken) {
        headers['Authorization'] = `Bearer ${sessionToken}`;
      }
      const res = await fetch('/api/workspace/agents', { headers });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.all_agents || []);
        setEnabledAgents(data.enabled_agents || []);
        setAgentConfigs(data.agent_configs || {});
        setCustomAgents(data.custom_agents || []);
        setError(null);
      } else {
        // Fallback if endpoint is not available yet
        const fallbackRes = await fetch('/api/agents');
        if (fallbackRes.ok) {
          const fallbackData = await fallbackRes.json();
          setAgents(fallbackData);
          setEnabledAgents(fallbackData.map(a => a.name));
        } else {
          setError('Failed to fetch workspace agents');
        }
      }
    } catch (err) {
      setError('Cannot reach backend');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaceAgents();
  }, [sessionToken]);

  // Scroll to bottom of sandbox console
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [testResult]);

  const handleToggleAgent = async (agentName) => {
    const isCurrentlyEnabled = enabledAgents.includes(agentName);
    let updatedEnabled = [];
    if (isCurrentlyEnabled) {
      updatedEnabled = enabledAgents.filter(name => name !== agentName);
    } else {
      updatedEnabled = [...enabledAgents, agentName];
    }

    // Optimistic update
    setEnabledAgents(updatedEnabled);

    try {
      const res = await fetch('/api/workspace/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ agents: updatedEnabled })
      });

      if (res.ok) {
        if (onToast) {
          onToast({
            title: isCurrentlyEnabled ? "Agent Disabled" : "Agent Enabled",
            message: `Successfully ${isCurrentlyEnabled ? 'disabled' : 'enabled'} the ${agentName.replace('_', ' ')} agent.`,
            level: "success"
          });
        }
      } else {
        throw new Error("Failed to update workspace agents configuration on backend");
      }
    } catch (err) {
      // Revert on error
      setEnabledAgents(enabledAgents);
      if (onToast) {
        onToast({
          title: "Update Failed",
          message: err.message || "An error occurred while updating agent configuration.",
          level: "error"
        });
      }
    }
  };

  const handleEditAgentClick = (agent) => {
    setIsEditing(agent.name);
    
    // Load config overrides or default system prompts
    const cfg = agentConfigs[agent.name] || {};
    const customDef = customAgents.find(ca => ca.name === agent.name);
    
    const defaultPrompt = customDef 
      ? customDef.system_prompt 
      : (agent.name === 'search' 
          ? "You are a helpful AI research assistant. Use tools to find current, accurate information from the web. Provide well-organized answers with key facts."
          : agent.name === 'code'
            ? "You are a brilliant software engineer. Use the secure sandbox tools to write, read, list files, or execute Python code to complete your programming and analysis tasks."
            : `You are JARVIS's ${agent.name.replace('_', ' ')} agent. Focus purely on executing your core role efficiently.`);
            
    setEditPrompt(cfg.system_prompt || defaultPrompt);
    setEditModel(cfg.model || (customDef ? customDef.model : "llama-3.3-70b-versatile"));
    setEditTemp(cfg.temperature !== undefined ? cfg.temperature : (customDef ? customDef.temperature : 0.3));
  };

  const handleSaveConfig = async () => {
    setIsSavingConfig(true);
    try {
      const res = await fetch('/api/workspace/agents/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          name: isEditing,
          system_prompt: editPrompt,
          model: editModel,
          temperature: parseFloat(editTemp)
        })
      });

      const data = await res.json();
      if (res.ok) {
        if (onToast) {
          onToast({
            title: "Configuration Saved",
            message: `Prompt overrides saved successfully for agent '${isEditing}'.`,
            level: "success"
          });
        }
        setIsEditing(null);
        fetchWorkspaceAgents();
      } else {
        throw new Error(data.detail || "Failed to save configuration.");
      }
    } catch (err) {
      if (onToast) {
        onToast({ title: "Save Failed", message: err.message, level: "error" });
      }
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleCreateAgent = async (e) => {
    e.preventDefault();
    if (!newName.trim() || !newDescription.trim() || !newPrompt.trim()) {
      if (onToast) {
        onToast({ title: "Validation Error", message: "Name, description, and system prompt are required.", level: "error" });
      }
      return;
    }

    const normalizedName = newName.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');

    setIsCreatingAgent(true);
    try {
      const res = await fetch('/api/workspace/agents/custom', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          name: normalizedName,
          description: newDescription.trim(),
          system_prompt: newPrompt.trim(),
          model: newModel,
          temperature: parseFloat(newTemp),
          base_agent: newBaseAgent || null
        })
      });

      const data = await res.json();
      if (res.ok) {
        if (onToast) {
          onToast({
            title: "Custom Agent Created",
            message: `Custom agent '${normalizedName}' created and enabled.`,
            level: "success"
          });
        }
        setIsCreating(false);
        setNewName("");
        setNewDescription("");
        setNewPrompt("");
        setNewModel("llama-3.3-70b-versatile");
        setNewTemp(0.3);
        setNewBaseAgent("");
        setTestQuery("");
        setTestResult("");
        fetchWorkspaceAgents();
      } else {
        throw new Error(data.detail || "Failed to create custom agent.");
      }
    } catch (err) {
      if (onToast) {
        onToast({ title: "Creation Failed", message: err.message, level: "error" });
      }
    } finally {
      setIsCreatingAgent(false);
    }
  };

  const handleTestAgent = async () => {
    if (!newPrompt.trim()) {
      if (onToast) {
        onToast({ title: "Validation Error", message: "System prompt is required to test the agent.", level: "error" });
      }
      return;
    }
    if (!testQuery.trim()) {
      return;
    }

    setIsTesting(true);
    setTestResult(prev => prev + `\n\n> ${testQuery}\n[Sandbox Executor] Running agent test execution...\n`);

    try {
      const res = await fetch('/api/workspace/agents/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          query: testQuery.trim(),
          system_prompt: newPrompt.trim(),
          model: newModel,
          temperature: parseFloat(newTemp),
          base_agent: newBaseAgent || null
        })
      });

      const data = await res.json();
      if (res.ok) {
        setTestResult(prev => prev + `${data.result}`);
        setTestQuery("");
      } else {
        throw new Error(data.detail || "Sandbox test execution failed.");
      }
    } catch (err) {
      setTestResult(prev => prev + `Error: ${err.message}`);
    } finally {
      setIsTesting(false);
    }
  };

  const handleDeleteAgent = async (agentName) => {
    if (!window.confirm(`Are you sure you want to permanently delete custom agent '${agentName}'?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/workspace/agents/custom/${agentName}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        }
      });

      const data = await res.json();
      if (res.ok) {
        if (onToast) {
          onToast({
            title: "Agent Deleted",
            message: `Custom agent '${agentName}' has been removed from workspace.`,
            level: "success"
          });
        }
        fetchWorkspaceAgents();
      } else {
        throw new Error(data.detail || "Failed to delete custom agent.");
      }
    } catch (err) {
      if (onToast) {
        onToast({ title: "Delete Failed", message: err.message, level: "error" });
      }
    }
  };

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="workspace-explorer-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}>
      <style>{`
        .agent-studio-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: rgba(4, 6, 12, 0.7);
          backdrop-filter: blur(8px);
          z-index: 999;
          opacity: 0;
          pointer-events: none;
          transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          transform: translate3d(0, 0, 0);
          backface-visibility: hidden;
        }
        .agents-grid {
          display: grid !important;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)) !important;
          grid-auto-rows: max-content !important;
          gap: 16px !important;
          overflow-y: auto !important;
          flex: 1 !important;
          padding-bottom: 20px !important;
          transform: translate3d(0, 0, 0);
        }
        .studio-select option {
          background-color: #0d121e !important;
          color: #cbd5e1 !important;
        }
        .agent-studio-overlay.open {
          opacity: 1;
          pointer-events: auto;
          animation: overlayFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .agent-studio-drawer {
          position: fixed;
          top: 0;
          right: 0;
          width: 520px;
          height: 100vh;
          background: rgba(13, 18, 30, 0.96);
          backdrop-filter: blur(25px);
          border-left: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: -15px 0 35px rgba(0, 0, 0, 0.6);
          z-index: 1000;
          display: flex;
          flex-direction: column;
          transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
          transform: translateX(100%);
          padding: 30px;
          box-sizing: border-box;
        }
        .agent-studio-drawer.open {
          transform: translateX(0);
          animation: drawerSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes overlayFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes drawerSlideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .studio-form-group {
          margin-bottom: 18px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .studio-label {
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 1px;
          font-weight: 700;
          color: #94a3b8;
        }
        .studio-input, .studio-textarea, .studio-select {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          color: #f1f5f9;
          padding: 10px 14px;
          font-size: 0.8rem;
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
          box-sizing: border-box;
          width: 100%;
        }
        .studio-input:focus, .studio-textarea:focus, .studio-select:focus {
          border-color: rgba(0, 212, 255, 0.4);
          background: rgba(255, 255, 255, 0.05);
          outline: none;
          box-shadow: 0 0 10px rgba(0, 212, 255, 0.15);
        }
        .studio-slider-container {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .studio-slider {
          flex: 1;
          height: 6px;
          border-radius: 3px;
          background: rgba(255, 255, 255, 0.1);
          outline: none;
          -webkit-appearance: none;
        }
        .studio-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #00d4ff;
          cursor: pointer;
          box-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
          transition: transform 0.1s ease;
        }
        .studio-slider::-webkit-slider-thumb:hover {
          transform: scale(1.2);
        }
        .studio-btn {
          background: linear-gradient(135deg, #00d4ff, #7c3aed);
          color: #ffffff;
          border: none;
          border-radius: 8px;
          padding: 10px 18px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .studio-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
        }
        .studio-btn:active {
          transform: translateY(0);
        }
        .studio-btn-secondary {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: #cbd5e1;
        }
        .studio-btn-secondary:hover {
          background: rgba(255, 255, 255, 0.1);
        }
        .delete-custom-btn:hover {
          color: rgba(244, 63, 94, 1) !important;
          background: rgba(244, 63, 94, 0.1) !important;
        }
        .edit-config-btn {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.06);
          color: #94a3b8;
          border-radius: 6px;
          padding: 6px 12px;
          font-size: 0.72rem;
          cursor: pointer;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-weight: 500;
        }
        .edit-config-btn:hover {
          background: rgba(0, 212, 255, 0.08);
          border-color: rgba(0, 212, 255, 0.3);
          color: #f1f5f9;
        }
        .search-input-container {
          position: relative;
          width: 280px;
        }
        .search-input-container input {
          width: 100%;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 20px;
          padding: 8px 16px 8px 36px;
          font-size: 0.8rem;
          color: #cbd5e1;
          transition: all 0.2s ease;
        }
        .search-input-container input:focus {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(0, 212, 255, 0.3);
          outline: none;
        }
        .search-icon-glass {
          position: absolute;
          left: 14px;
          top: 50%;
          transform: translateY(-50%);
          font-size: 0.8rem;
          color: #64748b;
          pointer-events: none;
        }
        .badge-studio {
          font-size: 0.62rem;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
      `}</style>

      {/* Overlay Backdrop */}
      {(isEditing || isCreating) && (
        <div 
          className="agent-studio-overlay open"
          onClick={() => {
            setIsEditing(null);
            setIsCreating(false);
          }}
        />
      )}

      {/* Slide-out Drawer: CONFIG EDITOR */}
      {isEditing && (
        <div className="agent-studio-drawer open">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <div>
              <h3 style={{ margin: 0, color: '#f1f5f9', fontSize: '1.1rem', textTransform: 'capitalize' }}>
                🔧 Edit Studio: {isEditing.replace('_', ' ')}
              </h3>
              <span style={{ fontSize: '0.72rem', color: '#64748b' }}>Configure agent-specific prompt guidelines and hyperparameters</span>
            </div>
            <button 
              onClick={() => setIsEditing(null)}
              style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
            <div className="studio-form-group">
              <label className="studio-label">System Prompt Guidelines</label>
              <textarea
                className="studio-textarea"
                rows={12}
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                placeholder="Provide clear system constraints and prompt logic for the agent..."
                style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.76rem', lineHeight: '1.45', resize: 'vertical' }}
              />
            </div>

            <div className="studio-form-group">
              <label className="studio-label">Model Target</label>
              <select
                className="studio-select"
                value={editModel}
                onChange={(e) => setEditModel(e.target.value)}
              >
                <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Smart / Default)</option>
                <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Fast / Lightweight)</option>
              </select>
            </div>

            <div className="studio-form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label className="studio-label">Model Temperature</label>
                <span style={{ fontSize: '0.76rem', color: '#00d4ff', fontFamily: 'monospace', fontWeight: 'bold' }}>{editTemp}</span>
              </div>
              <div className="studio-slider-container">
                <input
                  type="range"
                  className="studio-slider"
                  min="0"
                  max="1"
                  step="0.05"
                  value={editTemp}
                  onChange={(e) => setEditTemp(parseFloat(e.target.value))}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '24px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '20px' }}>
            <button 
              className="studio-btn studio-btn-secondary" 
              style={{ flex: 1 }}
              onClick={() => setIsEditing(null)}
            >
              Cancel
            </button>
            <button 
              className="studio-btn" 
              style={{ flex: 2 }}
              onClick={handleSaveConfig}
              disabled={isSavingConfig}
            >
              {isSavingConfig ? "Saving Overrides..." : "Save Custom Overrides"}
            </button>
          </div>
        </div>
      )}

      {/* Slide-out Drawer: CREATE CUSTOM AGENT */}
      {isCreating && (
        <div className="agent-studio-drawer open" style={{ width: '560px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ margin: 0, color: '#f1f5f9', fontSize: '1.1rem' }}>
                ✨ Agent Creator Studio
              </h3>
              <span style={{ fontSize: '0.72rem', color: '#64748b' }}>Deploy a specialized custom agent into your workspace</span>
            </div>
            <button 
              onClick={() => setIsCreating(false)}
              style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="studio-form-group" style={{ marginBottom: 0 }}>
                <label className="studio-label">Agent Unique Name</label>
                <input
                  type="text"
                  className="studio-input"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. security_auditor"
                />
              </div>
              <div className="studio-form-group" style={{ marginBottom: 0 }}>
                <label className="studio-label">Inherit Tools From</label>
                <select
                  className="studio-select"
                  value={newBaseAgent}
                  onChange={(e) => setNewBaseAgent(e.target.value)}
                >
                  <option value="">None (Pure Prompting)</option>
                  <option value="search">search (Web Search)</option>
                  <option value="code">code (Sandboxed Code Executor)</option>
                  <option value="scraper">scraper (Web Scraper)</option>
                  <option value="database">database (SQL Database Access)</option>
                  <option value="calendar">calendar (Calendar API)</option>
                  <option value="email">email (Email Delivery)</option>
                  <option value="maps">maps (Locations & Navigation)</option>
                  <option value="image_gen">image_gen (Image Generation)</option>
                </select>
              </div>
            </div>

            <div className="studio-form-group" style={{ marginBottom: 0 }}>
              <label className="studio-label">Short Description</label>
              <input
                type="text"
                className="studio-input"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="e.g. Scans files for structural security flaws and execution safety"
              />
            </div>

            <div className="studio-form-group" style={{ marginBottom: 0 }}>
              <label className="studio-label">System Prompt Guidelines</label>
              <textarea
                className="studio-textarea"
                rows={6}
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
                placeholder="Instruct the custom agent how to act, structure output, and use its inherited tools..."
                style={{ fontFamily: 'monospace', fontSize: '0.74rem' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '12px', alignItems: 'center' }}>
              <div className="studio-form-group" style={{ marginBottom: 0 }}>
                <label className="studio-label">Model Target</label>
                <select
                  className="studio-select"
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                >
                  <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile</option>
                  <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
                </select>
              </div>
              <div className="studio-form-group" style={{ marginBottom: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                  <label className="studio-label">Temperature</label>
                  <span style={{ fontSize: '0.74rem', color: '#00d4ff', fontFamily: 'monospace' }}>{newTemp}</span>
                </div>
                <div className="studio-slider-container">
                  <input
                    type="range"
                    className="studio-slider"
                    min="0"
                    max="1"
                    step="0.05"
                    value={newTemp}
                    onChange={(e) => setNewTemp(parseFloat(e.target.value))}
                  />
                </div>
              </div>
            </div>

            {/* Sandbox Test Console */}
            <div style={{ border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '10px', background: 'rgba(0, 0, 0, 0.15)', padding: '16px', display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px', display: 'block' }}>
                🔬 Dynamic Agent Test Sandbox
              </span>
              
              <div 
                style={{
                  background: '#040711',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  maxHeight: '130px',
                  overflowY: 'auto',
                  fontSize: '0.76rem',
                  color: '#34d399',
                  fontFamily: 'monospace',
                  border: '1px solid rgba(255, 255, 255, 0.03)',
                  whiteSpace: 'pre-wrap',
                  flex: 1,
                  minHeight: '60px'
                }}
              >
                {testResult || "Developer Console initialized. Input a prompt query below to run sandbox cycles on your agent configuration."}
                <div ref={consoleEndRef} />
              </div>

              <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                <input
                  type="text"
                  className="studio-input"
                  value={testQuery}
                  onChange={(e) => setTestQuery(e.target.value)}
                  placeholder="Test query: e.g. hello or check status..."
                  style={{ flex: 1 }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !isTesting) {
                      handleTestAgent();
                    }
                  }}
                />
                <button 
                  type="button"
                  className="studio-btn studio-btn-secondary"
                  style={{ padding: '0 14px' }}
                  onClick={handleTestAgent}
                  disabled={isTesting || !testQuery.trim()}
                >
                  {isTesting ? "Executing..." : "Run"}
                </button>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
            <button 
              type="button"
              className="studio-btn studio-btn-secondary" 
              style={{ flex: 1 }}
              onClick={() => setIsCreating(false)}
            >
              Cancel
            </button>
            <button 
              type="submit"
              className="studio-btn" 
              style={{ flex: 2 }}
              onClick={handleCreateAgent}
              disabled={isCreatingAgent}
            >
              {isCreatingAgent ? "Deploying Custom Agent..." : "Deploy Custom Agent"}
            </button>
          </div>
        </div>
      )}

      {/* Main Studio View Panel */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', padding: '0 4px', gap: '16px' }}>
        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 700, color: 'var(--text-tertiary)' }}>
          Workspace Studio ({enabledAgents.length} active / {agents.length} total)
        </span>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Search Bar */}
          <div className="search-input-container">
            <span className="search-icon-glass">🔍</span>
            <input
              type="text"
              placeholder="Search studio agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button
            className="studio-btn"
            style={{ padding: '8px 16px', fontSize: '0.76rem' }}
            onClick={() => setIsCreating(true)}
          >
            ➕ Custom Agent
          </button>
        </div>
      </div>

      {error && (
        <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--accent-rose)', fontSize: '0.8rem', background: 'rgba(244,63,94,0.05)', borderRadius: '8px', border: '1px solid rgba(244,63,94,0.1)', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {agents.length === 0 && !error && (
        <div style={{ textAlign: 'center', padding: '24px 8px', color: '#555876', fontSize: '0.8rem', background: 'rgba(0,0,0,0.15)', borderRadius: '8px', border: '1px dashed rgba(255,255,255,0.03)' }}>
          {isLoading ? "Loading agents..." : "No agents registered."}
        </div>
      )}

      <div className="agents-grid">
        {/* Create Card (always visible when searching is empty) */}
        {searchQuery === "" && (
          <div
            onClick={() => setIsCreating(true)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '24px',
              background: 'rgba(0, 212, 255, 0.01)',
              border: '1px dashed rgba(0, 212, 255, 0.25)',
              borderRadius: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              minHeight: '175px',
              textAlign: 'center',
              boxSizing: 'border-box'
            }}
            className="agent-card-grid-item"
          >
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '50%',
              background: 'rgba(0, 212, 255, 0.06)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.2rem',
              color: 'var(--accent-cyan, #00d4ff)',
              marginBottom: '12px',
              border: '1px solid rgba(0, 212, 255, 0.15)'
            }}>
              ➕
            </div>
            <strong style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>Deploy Custom Agent</strong>
            <span style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '6px', maxWidth: '200px' }}>
              Create an LLM agent with target prompt logic & base tools
            </span>
          </div>
        )}

        {/* Dynamic List */}
        {filteredAgents.map((agent) => {
          const iconData = AGENT_ICONS[agent.name] || { icon: '🔌' };
          const isActive = activeAgents.includes(agent.name);
          const isEnabled = enabledAgents.includes(agent.name);
          const isCustom = customAgents.some(ca => ca.name === agent.name);
          const isConfigured = agentConfigs[agent.name] !== undefined;

          const cardBackground = isActive 
            ? 'rgba(0, 212, 255, 0.04)' 
            : isEnabled 
              ? 'rgba(255, 255, 255, 0.015)' 
              : 'rgba(255, 255, 255, 0.003)';
          const cardBorder = isActive 
            ? '1px solid rgba(0, 212, 255, 0.25)' 
            : isEnabled 
              ? '1px solid rgba(255, 255, 255, 0.06)' 
              : '1px solid rgba(255, 255, 255, 0.015)';
          const cardOpacity = isEnabled ? 1 : 0.5;

          return (
            <div
              key={agent.name}
              className={`agent-card-grid-item ${isActive ? 'active-run' : ''}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                padding: '20px',
                background: cardBackground,
                border: cardBorder,
                borderRadius: '12px',
                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                position: 'relative',
                boxShadow: isActive ? '0 0 15px rgba(0, 212, 255, 0.04)' : 'none',
                opacity: cardOpacity,
                boxSizing: 'border-box',
                minHeight: '175px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: isCustom ? 'rgba(124, 58, 237, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                  border: isCustom ? '1px solid rgba(124, 58, 237, 0.2)' : 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.05rem'
                }}>
                  {iconData.icon}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <strong style={{ fontSize: '0.82rem', color: '#e2e8f0', textTransform: 'capitalize' }}>
                    {agent.name.replace('_', ' ')}
                  </strong>
                  <div style={{ display: 'flex', gap: '4px', marginTop: '2px', alignItems: 'center' }}>
                    {isCustom && (
                      <span className="badge-studio" style={{ background: 'rgba(124, 58, 237, 0.15)', color: '#a78bfa' }}>
                        Custom
                      </span>
                    )}
                    {isConfigured && (
                      <span className="badge-studio" style={{ background: 'rgba(0, 212, 255, 0.12)', color: '#22d3ee' }}>
                        Configured
                      </span>
                    )}
                  </div>
                </div>
                
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {isActive && (
                    <span
                      style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: 'var(--accent-cyan)',
                        boxShadow: '0 0 8px var(--accent-cyan)'
                      }}
                      title="Running task"
                    />
                  )}
                  <button
                    onClick={() => handleToggleAgent(agent.name)}
                    style={{
                      position: 'relative',
                      width: '34px',
                      height: '18px',
                      borderRadius: '9px',
                      background: isEnabled ? 'linear-gradient(135deg, #00d4ff, #7c3aed)' : 'rgba(255,255,255,0.08)',
                      border: '1px solid rgba(255,255,255,0.05)',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center'
                    }}
                    title={isEnabled ? "Disable Agent" : "Enable Agent"}
                  >
                    <div style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '50%',
                      background: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                      transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                      transform: isEnabled ? 'translateX(18px)' : 'translateX(2px)'
                    }} />
                  </button>
                </div>
              </div>
              
              <p style={{ fontSize: '0.74rem', color: '#94a3b8', lineHeight: '1.45', margin: '0 0 14px 0', flex: 1 }}>
                {agent.description}
              </p>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: 'auto' }}>
                <button
                  className="edit-config-btn"
                  onClick={() => handleEditAgentClick(agent)}
                  title="Tune Prompt & Hyperparameters"
                >
                  ⚙️ Studio Tuning
                </button>
                
                {isCustom && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteAgent(agent.name);
                    }}
                    style={{
                      background: 'rgba(244, 63, 94, 0.05)',
                      border: '1px solid rgba(244, 63, 94, 0.1)',
                      cursor: 'pointer',
                      fontSize: '0.72rem',
                      color: 'rgba(244, 63, 94, 0.8)',
                      padding: '5px 8px',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      transition: 'all 0.2s ease',
                      marginLeft: 'auto'
                    }}
                    className="delete-custom-btn"
                    title="Delete Custom Agent"
                  >
                    🗑️ Delete
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
