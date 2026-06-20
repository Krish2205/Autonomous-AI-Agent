import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient';

export default function Login({ onAuthSuccess }) {
  const [authMode, setAuthMode] = useState('local'); // 'local' or 'supabase'
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // Local Developer Mode state
  const [localUser, setLocalUser] = useState('developer');
  const [customUser, setCustomUser] = useState('');
  const [customWorkspaces, setCustomWorkspaces] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis_custom_workspaces');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error("Failed to load custom workspaces:", e);
      return [];
    }
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [allAgents, setAllAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]);

  // Fetch available system agents
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch('/api/agents');
        if (res.ok) {
          const data = await res.json();
          setAllAgents(data);
          // Preselect all agents by default
          setSelectedAgents(data.map(a => a.name));
        }
      } catch (err) {
        console.error("Failed to fetch system agents:", err);
      }
    };
    fetchAgents();
  }, []);

  // Fetch health check to determine auth provider
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          setAuthMode(data.auth_provider || 'local');
        }
      } catch (err) {
        console.error("Failed to fetch auth mode from health endpoint, defaulting to local:", err);
      }
    };
    fetchHealth();
  }, []);

  const handleLocalSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');
    
    let selectedUser = '';
    let sanitizedUser = '';

    if (localUser === 'custom') {
      selectedUser = customUser.trim();
      sanitizedUser = selectedUser.toLowerCase().replace(/[^a-z0-9-_]/g, '');
    } else {
      const matched = customWorkspaces.find(w => w.id === localUser);
      if (matched) {
        selectedUser = matched.name;
        sanitizedUser = matched.id;
      } else {
        selectedUser = localUser;
        sanitizedUser = localUser.toLowerCase().replace(/[^a-z0-9-_]/g, '');
      }
    }

    if (!selectedUser || !sanitizedUser) {
      setErrorMsg('Please enter a valid username.');
      setIsLoading(false);
      return;
    }

    if (localUser === 'custom') {
      const exists = customWorkspaces.some(w => w.id === sanitizedUser);
      if (!exists) {
        const updated = [...customWorkspaces, { id: sanitizedUser, name: selectedUser }];
        setCustomWorkspaces(updated);
        localStorage.setItem('jarvis_custom_workspaces', JSON.stringify(updated));
      }

      // Initialize selected agents on the backend for this custom workspace
      try {
        await fetch('/api/workspace/agents', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sanitizedUser}`
          },
          body: JSON.stringify({ agents: selectedAgents })
        });
      } catch (err) {
        console.error("Failed to initialize custom workspace agents configuration on backend", err);
      }
    }

    setTimeout(() => {
      setIsLoading(false);
      onAuthSuccess({
        id: sanitizedUser,
        email: `${sanitizedUser}@local-jarvis.internal`,
        user_metadata: { full_name: selectedUser }
      }, sanitizedUser); // token = username for local dev
    }, 600);
  };

  const handleSupabaseSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    if (!supabase) {
      setErrorMsg('Supabase client is not initialized. Check your environment variables.');
      setIsLoading(false);
      return;
    }

    try {
      if (isSignUp) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: email.split('@')[0]
            }
          }
        });
        if (error) throw error;
        
        if (data.session) {
          onAuthSuccess(data.user, data.session.access_token);
        } else {
          setSuccessMsg('Verification email sent! Please check your inbox.');
        }
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password
        });
        if (error) throw error;
        if (data.session) {
          onAuthSuccess(data.user, data.session.access_token);
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'An error occurred during authentication.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-screen">
      {/* Scope styles directly in the component for portability and clean modularity */}
      <style>{`
        .login-screen {
          position: fixed;
          inset: 0;
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #06060f;
          font-family: 'Inter', system-ui, -apple-system, sans-serif;
          color: #e8eaff;
          overflow: hidden;
        }

        .login-card {
          width: 420px;
          padding: 40px;
          background: rgba(12, 12, 35, 0.65);
          border: 1px solid rgba(100, 120, 255, 0.15);
          border-radius: 20px;
          backdrop-filter: blur(25px);
          -webkit-backdrop-filter: blur(25px);
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 40px rgba(0, 212, 255, 0.05);
          animation: cardSlideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
          position: relative;
        }

        @keyframes cardSlideUp {
          from { opacity: 0; transform: translateY(40px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .login-logo {
          display: flex;
          justify-content: center;
          margin-bottom: 24px;
        }

        .logo-ring-outer {
          position: relative;
          width: 60px;
          height: 60px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .logo-ring {
          position: absolute;
          inset: 0;
          border: 3px solid #00d4ff;
          border-radius: 50%;
          animation: pulse-ring 3s ease-in-out infinite;
        }

        .logo-core {
          width: 26px;
          height: 26px;
          background: #00d4ff;
          border-radius: 50%;
          box-shadow: 0 0 15px #00d4ff, 0 0 30px rgba(0, 212, 255, 0.4);
        }

        .login-header {
          text-align: center;
          margin-bottom: 30px;
        }

        .login-title {
          font-size: 1.8rem;
          font-weight: 800;
          letter-spacing: 4px;
          text-transform: uppercase;
          background: linear-gradient(135deg, #00d4ff, #7c3aed);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 6px;
        }

        .login-subtitle {
          font-size: 0.75rem;
          color: #8b8fad;
          text-transform: uppercase;
          letter-spacing: 2px;
          font-weight: 500;
        }

        .auth-badge {
          display: inline-block;
          margin-top: 10px;
          padding: 4px 12px;
          font-size: 0.65rem;
          font-weight: 600;
          letter-spacing: 1px;
          text-transform: uppercase;
          border-radius: 99px;
          background: rgba(0, 212, 255, 0.1);
          border: 1px solid rgba(0, 212, 255, 0.25);
          color: #00d4ff;
        }

        .auth-badge.local {
          background: rgba(245, 158, 11, 0.1);
          border-color: rgba(245, 158, 11, 0.25);
          color: #f59e0b;
        }

        .form-group {
          margin-bottom: 20px;
          text-align: left;
        }

        .form-label {
          display: block;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: #8b8fad;
          margin-bottom: 8px;
        }

        .form-input, .form-select {
          width: 100%;
          padding: 12px 16px;
          background: rgba(6, 6, 15, 0.6);
          border: 1px solid rgba(100, 120, 255, 0.15);
          border-radius: 10px;
          color: #e8eaff;
          font-size: 0.9rem;
          outline: none;
          transition: all 0.2s ease;
        }

        .form-input:focus, .form-select:focus {
          border-color: #00d4ff;
          box-shadow: 0 0 10px rgba(0, 212, 255, 0.15);
        }

        .login-btn {
          width: 100%;
          padding: 14px;
          margin-top: 10px;
          background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(124, 58, 237, 0.2));
          border: 1px solid rgba(100, 120, 255, 0.2);
          border-radius: 10px;
          color: #e8eaff;
          font-weight: 700;
          font-size: 0.95rem;
          letter-spacing: 1px;
          text-transform: uppercase;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .login-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, rgba(0, 212, 255, 0.35), rgba(124, 58, 237, 0.35));
          border-color: #00d4ff;
          box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
          transform: translateY(-1px);
        }

        .login-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .toggle-auth-mode {
          display: block;
          text-align: center;
          margin-top: 20px;
          font-size: 0.8rem;
          color: #8b8fad;
          cursor: pointer;
          background: none;
          border: none;
          width: 100%;
          transition: color 0.2s ease;
        }

        .toggle-auth-mode:hover {
          color: #00d4ff;
        }

        .alert {
          padding: 12px;
          border-radius: 8px;
          font-size: 0.8rem;
          margin-bottom: 20px;
          line-height: 1.4;
          text-align: left;
        }

        .alert.error {
          background: rgba(244, 63, 94, 0.1);
          border: 1px solid rgba(244, 63, 94, 0.25);
          color: #f43f5e;
        }

        .alert.success {
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.25);
          color: #22c55e;
        }

        .delete-workspace-btn {
          padding: 0 16px;
          background: rgba(244, 63, 94, 0.15);
          border: 1px solid rgba(244, 63, 94, 0.3);
          color: #ff4a6b;
          border-radius: 10px;
          font-size: 0.95rem;
          font-weight: bold;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .delete-workspace-btn:hover {
          background: rgba(244, 63, 94, 0.3);
          border-color: #f43f5e;
          box-shadow: 0 0 12px rgba(244, 63, 94, 0.25);
          transform: scale(1.05);
        }
      `}</style>

      <div className="login-card">
        <div className="login-logo">
          <div className="logo-ring-outer">
            <div className="logo-ring" />
            <div className="logo-core" />
          </div>
        </div>

        <div className="login-header">
          <h2 className="login-title">JARVIS</h2>
          <p className="login-subtitle">AI Operating System Portal</p>
          {authMode === 'supabase' ? (
            <span className="auth-badge">Supabase Active</span>
          ) : (
            <span className="auth-badge local">Development Mode</span>
          )}
        </div>

        {errorMsg && <div className="alert error">{errorMsg}</div>}
        {successMsg && <div className="alert success">{successMsg}</div>}

        {authMode === 'local' ? (
          <form onSubmit={handleLocalSubmit}>
            <div className="form-group">
              <label className="form-label">Select Workspace Profile</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  className="form-select"
                  value={localUser}
                  onChange={(e) => setLocalUser(e.target.value)}
                  style={{ flex: 1 }}
                >
                  <option value="developer">Developer (developer)</option>
                  <option value="analyst">Data Analyst (analyst)</option>
                  <option value="designer">Designer (designer)</option>
                  <option value="manager">Project Manager (manager)</option>
                  <option value="guest">Guest User (guest)</option>
                  {customWorkspaces.map(w => (
                    <option key={w.id} value={w.id}>{w.name} ({w.id})</option>
                  ))}
                  <option value="custom">-- Create Custom Workspace --</option>
                </select>
                {customWorkspaces.some(w => w.id === localUser) && (
                  <button
                    type="button"
                    onClick={async (e) => {
                      e.stopPropagation();
                      const matched = customWorkspaces.find(w => w.id === localUser);
                      const displayName = matched ? matched.name : localUser;
                      
                      const confirmed = window.confirm(`Are you sure you want to delete the workspace "${displayName}" and ALL of its conversation history, uploaded files, and database tables? This action is permanent.`);
                      if (!confirmed) return;

                      setIsLoading(true);
                      setErrorMsg('');
                      setSuccessMsg('');

                      try {
                        const res = await fetch(`/api/workspace/${localUser}`, {
                          method: 'DELETE',
                          headers: {
                            'Authorization': `Bearer ${localUser}`
                          }
                        });

                        if (!res.ok) {
                          const errData = await res.json().catch(() => null);
                          throw new Error(errData?.detail || `Failed to delete backend data (status: ${res.status})`);
                        }

                        localStorage.removeItem(`jarvis_conversations_${localUser}`);

                        const updated = customWorkspaces.filter(w => w.id !== localUser);
                        setCustomWorkspaces(updated);
                        localStorage.setItem('jarvis_custom_workspaces', JSON.stringify(updated));

                        setLocalUser('developer');
                        setSuccessMsg(`Workspace "${displayName}" and all its data was successfully deleted.`);
                      } catch (err) {
                        setErrorMsg(`Error deleting workspace data: ${err.message}`);
                      } finally {
                        setIsLoading(false);
                      }
                    }}
                    className="delete-workspace-btn"
                    title="Delete Workspace and Data"
                    disabled={isLoading}
                  >
                    {isLoading ? '...' : '✕'}
                  </button>
                )}
              </div>
            </div>

            {localUser === 'custom' && (
              <>
                <div className="form-group" style={{ animation: 'fadeIn 0.3s ease-out' }}>
                  <label className="form-label">Workspace Name</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. jarvis-admin"
                    value={customUser}
                    onChange={(e) => setCustomUser(e.target.value)}
                    maxLength={25}
                    required
                  />
                </div>
                
                <div className="form-group" style={{ animation: 'fadeIn 0.3s ease-out', marginTop: '16px' }}>
                  <label className="form-label">Select Workspace Agents</label>
                  <div style={{
                    maxHeight: '180px',
                    overflowY: 'auto',
                    background: 'rgba(6, 6, 15, 0.6)',
                    border: '1px solid rgba(100, 120, 255, 0.15)',
                    borderRadius: '10px',
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    {allAgents.map(agent => (
                      <label key={agent.name} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.85rem' }}>
                        <input
                          type="checkbox"
                          checked={selectedAgents.includes(agent.name)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedAgents(prev => [...prev, agent.name]);
                            } else {
                              setSelectedAgents(prev => prev.filter(name => name !== agent.name));
                            }
                          }}
                          style={{
                            cursor: 'pointer',
                            accentColor: '#00d4ff'
                          }}
                        />
                        <span style={{ textTransform: 'capitalize', color: '#cbd5e1' }}>
                          {agent.name.replace('_', ' ')}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}

            <button type="submit" className="login-btn" disabled={isLoading}>
              {isLoading ? 'Booting Space...' : 'Load Workspace'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSupabaseSubmit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="login-btn" disabled={isLoading}>
              {isLoading ? 'Verifying...' : isSignUp ? 'Create Account' : 'Authenticate'}
            </button>

            <button
              type="button"
              className="toggle-auth-mode"
              onClick={() => setIsSignUp(!isSignUp)}
            >
              {isSignUp ? 'Already registered? Sign In' : "Don't have an account? Sign Up"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
