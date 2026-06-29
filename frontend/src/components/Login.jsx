import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient';

const PROFILE_OPTIONS = [
  { id: 'developer', name: 'Developer Suite', category: 'Engineering & IT', emoji: '💻', desc: 'Full-stack software engineering, terminal code execution & debugging', agents: ['Code', 'Search', 'Analyse', 'Summary', 'DevOps', 'Cloud Infra', 'GitHub'] },
  { id: 'cloud_devops', name: 'Cloud & DevOps SRE', category: 'Engineering & IT', emoji: '☁️', desc: 'Terraform IaC stacks, Kubernetes cluster health & CI/CD automation', agents: ['Cloud Infra', 'DevOps', 'GitHub', 'SecOps', 'Code'] },
  { id: 'cybersec_auditor', name: 'Cybersecurity Audit', category: 'Engineering & IT', emoji: '🛡️', desc: 'CVE vulnerability audits, syslog threat triage & zero-trust compliance', agents: ['SecOps', 'Compliance', 'Analyse', 'Summary'] },
  { id: 'financial_analyst', name: 'Financial Analyst', category: 'Finance & Legal', emoji: '📈', desc: 'Executive P&L statements, cash flow projections & stock fundamentals', agents: ['Financial Reporting', 'Market Intel', 'Finance', 'Visualization'] },
  { id: 'legal_ops', name: 'Legal & HR Operations', category: 'Finance & Legal', emoji: '⚖️', desc: 'Contract NDA risk evaluation, indemnification caps & talent hiring rubrics', agents: ['Legal Contract', 'Talent Ops', 'Compliance', 'Email'] },
  { id: 'healthcare_researcher', name: 'Medical RAG Research', category: 'Research & Growth', emoji: '🧬', desc: 'PubMed literature indexing, clinical trial phase synthesis & pharmacology', agents: ['Biomedical RAG', 'Analyse', 'Summary', 'Search'] },
  { id: 'creative_marketer', name: 'Growth Marketing', category: 'Research & Growth', emoji: '🚀', desc: 'SEO keyword strategies, viral ad copy hooks & production video scripts', agents: ['Marketing Campaign', 'Multimedia Processor', 'Image Gen', 'Search'] },
  { id: 'analyst', name: 'Data Intelligence', category: 'Research & Growth', emoji: '📊', desc: 'Relational SQLite SQL operations, dynamic charts & statistical matrices', agents: ['Database', 'Visualization', 'Analyse', 'Summary'] },
  { id: 'designer', name: 'Visual Creative Suite', category: 'Research & Growth', emoji: '🎨', desc: 'AI image generation, UI/UX mockups & high-resolution visual assets', agents: ['Image Gen', 'Visualization', 'Summary'] },
  { id: 'manager', name: 'Executive Project Hub', category: 'General & Executive', emoji: '📋', desc: 'Cross-functional task delegation, automated email dispatch & calendar sync', agents: ['Summary', 'Email', 'Calendar', 'Notification', 'Search'] },
  { id: 'guest', name: 'General AI Workstation', category: 'General & Executive', emoji: '👤', desc: 'Omni-purpose conversational AI assistant and web search exploration', agents: ['Search', 'Summary', 'Analyse', 'Code'] },
];

export default function Login({ onAuthSuccess }) {
  const [authMode, setAuthMode] = useState('local');
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // Workspace State
  const [localUser, setLocalUser] = useState('developer');
  const [activeCategory, setActiveCategory] = useState('All');
  const [customUser, setCustomUser] = useState('');
  const [customWorkspaces, setCustomWorkspaces] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis_custom_workspaces');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [allAgents, setAllAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch('/api/agents');
        if (res.ok) {
          const data = await res.json();
          setAllAgents(data);
          setSelectedAgents(data.map(a => a.name));
        }
      } catch (err) {
        console.error("Failed to fetch system agents:", err);
      }
    };
    fetchAgents();
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          setAuthMode(data.auth_provider || 'local');
        }
      } catch (err) {
        console.error("Defaulting to local auth mode:", err);
      }
    };
    fetchHealth();
  }, []);

  const executeLaunch = async (targetUser = localUser) => {
    setIsLoading(true);
    setErrorMsg('');
    
    let selectedUser = '';
    let sanitizedUser = '';

    if (targetUser === 'custom') {
      selectedUser = customUser.trim();
      sanitizedUser = selectedUser.toLowerCase().replace(/[^a-z0-9-_]/g, '');
    } else {
      const matched = customWorkspaces.find(w => w.id === targetUser);
      if (matched) {
        selectedUser = matched.name;
        sanitizedUser = matched.id;
      } else {
        selectedUser = targetUser;
        sanitizedUser = targetUser.toLowerCase().replace(/[^a-z0-9-_]/g, '');
      }
    }

    if (!selectedUser || !sanitizedUser) {
      setErrorMsg('Please specify a valid workspace name before launching.');
      setIsLoading(false);
      return;
    }

    if (targetUser === 'custom') {
      const exists = customWorkspaces.some(w => w.id === sanitizedUser);
      if (!exists) {
        const updated = [...customWorkspaces, { id: sanitizedUser, name: selectedUser }];
        setCustomWorkspaces(updated);
        localStorage.setItem('jarvis_custom_workspaces', JSON.stringify(updated));
      }

      try {
        await fetch(`/api/workspace/${sanitizedUser}/agents`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sanitizedUser}`
          },
          body: JSON.stringify({ agents: selectedAgents })
        });
      } catch (err) {
        console.error("Failed to configure custom workspace agents:", err);
      }
    }

    localStorage.setItem('jarvis_session_token', sanitizedUser);
    localStorage.setItem('jarvis_user_id', sanitizedUser);
    
    if (onAuthSuccess) {
      onAuthSuccess(
        { id: sanitizedUser, email: `${selectedUser}@local.jarvis`, user_metadata: { full_name: selectedUser } },
        sanitizedUser
      );
    }
    setIsLoading(false);
  };

  const categories = ['All', 'Engineering & IT', 'Finance & Legal', 'Research & Growth', 'General & Executive'];

  const filteredProfiles = activeCategory === 'All' 
    ? PROFILE_OPTIONS 
    : PROFILE_OPTIONS.filter(p => p.category === activeCategory);

  const selectedProfileObj = PROFILE_OPTIONS.find(p => p.id === localUser) || customWorkspaces.find(w => w.id === localUser);

  return (
    <div className="premium-portal">
      <style>{`
        .premium-portal {
          position: fixed;
          inset: 0;
          z-index: 1000;
          display: flex;
          flex-direction: column;
          background: radial-gradient(circle at 50% -20%, #151942 0%, #060713 70%);
          font-family: 'Inter', system-ui, -apple-system, sans-serif;
          color: #f1f5f9;
          overflow-y: auto;
          padding: 24px 24px 100px;
        }

        .portal-wrapper {
          width: 100%;
          max-width: 1360px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        /* Top Header */
        .portal-top-bar {
          display: flex;
          flex-direction: column;
          align-items: center;
          margin-bottom: 20px;
          text-align: center;
        }

        .hero-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 12px;
          background: rgba(0, 212, 255, 0.08);
          border: 1px solid rgba(0, 212, 255, 0.25);
          border-radius: 99px;
          color: #00d4ff;
          font-size: 0.68rem;
          font-weight: 700;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          margin-bottom: 10px;
          box-shadow: 0 0 15px rgba(0, 212, 255, 0.12);
        }

        .hero-title {
          font-size: 2.1rem;
          font-weight: 900;
          letter-spacing: 6px;
          text-transform: uppercase;
          background: linear-gradient(135deg, #ffffff 0%, #00d4ff 50%, #a78bfa 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin: 0 0 6px 0;
          line-height: 1.1;
        }

        .hero-sub {
          font-size: 0.82rem;
          color: #94a3b8;
          max-width: 540px;
          line-height: 1.4;
          font-weight: 400;
        }

        /* Filter Tabs */
        .category-nav {
          display: flex;
          gap: 8px;
          margin-bottom: 24px;
          background: rgba(15, 20, 45, 0.6);
          padding: 4px;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          backdrop-filter: blur(16px);
        }

        .category-tab {
          padding: 6px 14px;
          border-radius: 8px;
          font-size: 0.76rem;
          font-weight: 600;
          color: #94a3b8;
          background: transparent;
          border: none;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .category-tab:hover {
          color: #f1f5f9;
        }

        .category-tab.active {
          background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(124, 58, 237, 0.2));
          color: #00d4ff;
          border: 1px solid rgba(0, 212, 255, 0.3);
          box-shadow: 0 4px 12px rgba(0, 212, 255, 0.15);
        }

        /* Grid Cards */
        .workspace-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
          gap: 16px;
          width: 100%;
        }

        .premium-card {
          position: relative;
          padding: 18px;
          background: rgba(13, 17, 38, 0.65);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          backdrop-filter: blur(25px);
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          text-align: left;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }

        .premium-card:hover {
          border-color: rgba(0, 212, 255, 0.4);
          transform: translateY(-4px);
          background: rgba(18, 24, 54, 0.85);
          box-shadow: 0 14px 30px rgba(0, 0, 0, 0.4), 0 0 25px rgba(0, 212, 255, 0.15);
        }

        .premium-card.active {
          border-color: #00d4ff;
          background: radial-gradient(circle at 100% 0%, rgba(124, 58, 237, 0.15) 0%, rgba(0, 212, 255, 0.15) 100%), rgba(15, 21, 48, 0.9);
          box-shadow: 0 0 25px rgba(0, 212, 255, 0.25), inset 0 0 12px rgba(0, 212, 255, 0.1);
        }

        .active-indicator {
          position: absolute;
          top: 14px;
          right: 14px;
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 3px 8px;
          background: #00d4ff;
          color: #060713;
          border-radius: 99px;
          font-size: 0.62rem;
          font-weight: 800;
          letter-spacing: 1px;
          text-transform: uppercase;
          box-shadow: 0 0 10px #00d4ff;
        }

        .card-top {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 10px;
        }

        .icon-box {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.3rem;
          flex-shrink: 0;
        }

        .premium-card.active .icon-box {
          background: rgba(0, 212, 255, 0.15);
          border-color: rgba(0, 212, 255, 0.4);
          box-shadow: 0 0 12px rgba(0, 212, 255, 0.2);
        }

        .card-meta {
          display: flex;
          flex-direction: column;
        }

        .card-title {
          font-size: 1.02rem;
          font-weight: 800;
          color: #f8fafc;
          margin: 0 0 2px 0;
        }

        .card-category {
          font-size: 0.65rem;
          color: #00d4ff;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.8px;
        }

        .card-body {
          font-size: 0.78rem;
          color: #94a3b8;
          line-height: 1.4;
          margin-bottom: 14px;
        }

        .card-footer {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          padding-top: 12px;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
        }

        .agent-pill {
          padding: 2px 7px;
          border-radius: 5px;
          font-size: 0.62rem;
          font-weight: 600;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: #cbd5e1;
        }

        .premium-card.active .agent-pill {
          background: rgba(0, 212, 255, 0.1);
          border-color: rgba(0, 212, 255, 0.25);
          color: #00d4ff;
        }

        /* Floating Dock */
        .floating-dock {
          position: fixed;
          bottom: 20px;
          left: 50%;
          transform: translateX(-50%);
          width: 90%;
          max-width: 720px;
          padding: 12px 22px;
          background: rgba(10, 13, 30, 0.94);
          backdrop-filter: blur(25px);
          border: 1px solid rgba(0, 212, 255, 0.4);
          border-radius: 20px;
          box-shadow: 0 15px 40px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 212, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          z-index: 100;
        }

        .dock-info {
          display: flex;
          align-items: center;
          gap: 12px;
          text-align: left;
        }

        .dock-emoji {
          font-size: 1.6rem;
        }

        .dock-label {
          font-size: 0.65rem;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 1.2px;
          font-weight: 700;
        }

        .dock-title {
          font-size: 1rem;
          font-weight: 800;
          color: #00d4ff;
        }

        .launch-action-btn {
          padding: 12px 28px;
          background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%);
          border: none;
          border-radius: 12px;
          color: #ffffff;
          font-weight: 800;
          font-size: 0.88rem;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 0 20px rgba(0, 212, 255, 0.35);
          white-space: nowrap;
        }

        .launch-action-btn:hover:not(:disabled) {
          transform: scale(1.03);
          box-shadow: 0 0 40px rgba(0, 212, 255, 0.7);
        }

        /* Config expander */
        .custom-panel {
          width: 100%;
          max-width: 840px;
          margin-top: 24px;
          padding: 28px;
          background: rgba(13, 17, 38, 0.8);
          border: 1px solid rgba(0, 212, 255, 0.3);
          border-radius: 20px;
          text-align: left;
        }

        .custom-input {
          width: 100%;
          padding: 14px 18px;
          background: rgba(6, 8, 20, 0.8);
          border: 1px solid rgba(100, 120, 255, 0.2);
          border-radius: 12px;
          color: #fff;
          font-size: 0.95rem;
          margin-top: 8px;
          margin-bottom: 20px;
          outline: none;
        }

        .custom-input:focus {
          border-color: #00d4ff;
          box-shadow: 0 0 15px rgba(0, 212, 255, 0.25);
        }
      `}</style>

      <div className="portal-wrapper">
        
        {/* Top Header */}
        <header className="portal-top-bar">
          <div className="hero-badge">
            <span style={{ animation: 'pulse 2s infinite' }}>⚡</span> JARVIS AI Operating System
          </div>
          <h1 className="hero-title">Command Center</h1>
          <p className="hero-sub">Select an enterprise workspace profile tailored with multi-agent intelligence suites.</p>
        </header>

        {/* Category Navigation */}
        <nav className="category-nav">
          {categories.map(cat => (
            <button
              key={cat}
              className={`category-tab ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </nav>

        {errorMsg && <div style={{ padding: '14px', background: 'rgba(244,63,94,0.15)', border: '1px solid #f43f5e', borderRadius: '12px', color: '#f43f5e', marginBottom: '20px', width: '100%', maxWidth: '840px' }}>{errorMsg}</div>}

        {/* Enterprise Cards Grid */}
        <div className="workspace-grid">
          {filteredProfiles.map(profile => {
            const isSelected = localUser === profile.id;
            return (
              <div
                key={profile.id}
                className={`premium-card ${isSelected ? 'active' : ''}`}
                onClick={() => {
                  setLocalUser(profile.id);
                  executeLaunch(profile.id);
                }}
              >
                {isSelected && <div className="active-indicator">Active</div>}
                <div>
                  <div className="card-top">
                    <div className="icon-box">{profile.emoji}</div>
                    <div className="card-meta">
                      <h3 className="card-title">{profile.name}</h3>
                      <span className="card-category">{profile.category}</span>
                    </div>
                  </div>
                  <p className="card-body">{profile.desc}</p>
                </div>
                <div className="card-footer">
                  {profile.agents.map(a => <span key={a} className="agent-pill">{a}</span>)}
                </div>
              </div>
            );
          })}

          {/* Custom Workspaces */}
          {customWorkspaces.map(w => {
            const isSelected = localUser === w.id;
            return (
              <div
                key={w.id}
                className={`premium-card ${isSelected ? 'active' : ''}`}
                onClick={() => {
                  setLocalUser(w.id);
                  executeLaunch(w.id);
                }}
              >
                {isSelected && <div className="active-indicator">Active</div>}
                <div>
                  <div className="card-top">
                    <div className="icon-box">📂</div>
                    <div className="card-meta">
                      <h3 className="card-title">{w.name}</h3>
                      <span className="card-category">Custom Workspace</span>
                    </div>
                  </div>
                  <p className="card-body">Custom environment profile with dedicated agent tool bindings.</p>
                </div>
                <div className="card-footer">
                  <span className="agent-pill">Custom Environment</span>
                </div>
              </div>
            );
          })}

          {/* Create Custom Workspace Card */}
          <div
            className={`premium-card ${localUser === 'custom' ? 'active' : ''}`}
            style={{ borderStyle: 'dashed', borderColor: localUser === 'custom' ? '#00d4ff' : 'rgba(0,212,255,0.3)' }}
            onClick={() => setLocalUser('custom')}
          >
            {localUser === 'custom' && <div className="active-indicator">Configuring</div>}
            <div>
              <div className="card-top">
                <div className="icon-box" style={{ color: '#00d4ff' }}>✨</div>
                <div className="card-meta">
                  <h3 className="card-title" style={{ color: '#00d4ff' }}>+ Create Custom</h3>
                  <span className="card-category">Personalized Tools</span>
                </div>
              </div>
              <p className="card-body">Configure custom agent permissions and tool suites from scratch.</p>
            </div>
            <div className="card-footer">
              <span className="agent-pill" style={{ borderColor: '#00d4ff', color: '#00d4ff' }}>Custom Agent Suite</span>
            </div>
          </div>
        </div>

        {/* Custom Config Expander Panel */}
        {localUser === 'custom' && (
          <div className="custom-panel">
            <h3 style={{ margin: '0 0 16px 0', color: '#00d4ff' }}>⚙️ Custom Workspace Configuration</h3>
            <label style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Workspace Profile Name</label>
            <input
              type="text"
              className="custom-input"
              placeholder="e.g. quantum-ai-lab"
              value={customUser}
              onChange={(e) => setCustomUser(e.target.value)}
            />
            <label style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, display: 'block', marginBottom: '10px' }}>Enable Specialized Agent Tools</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px', maxHeight: '180px', overflowY: 'auto', padding: '12px', background: 'rgba(6,8,20,0.6)', borderRadius: '12px', marginBottom: '20px' }}>
              {allAgents.map(agent => (
                <label key={agent.name} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem' }}>
                  <input
                    type="checkbox"
                    checked={selectedAgents.includes(agent.name)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedAgents(prev => [...prev, agent.name]);
                      else setSelectedAgents(prev => prev.filter(n => n !== agent.name));
                    }}
                    style={{ accentColor: '#00d4ff' }}
                  />
                  <span style={{ textTransform: 'capitalize' }}>{agent.name.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
            <button
              type="button"
              style={{
                width: '100%',
                padding: '14px',
                background: 'linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%)',
                border: 'none',
                borderRadius: '12px',
                color: '#fff',
                fontWeight: 800,
                fontSize: '0.95rem',
                letterSpacing: '1.5px',
                textTransform: 'uppercase',
                cursor: 'pointer',
                boxShadow: '0 0 20px rgba(0, 212, 255, 0.35)'
              }}
              disabled={isLoading}
              onClick={() => executeLaunch('custom')}
            >
              {isLoading ? 'INITIALIZING WORKSPACE...' : 'CREATE & LAUNCH WORKSPACE ⚡'}
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
