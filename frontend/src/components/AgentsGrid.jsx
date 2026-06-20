import { useState, useEffect } from 'react';

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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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

  return (
    <div className="workspace-explorer-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', padding: '0 4px' }}>
        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 700, color: 'var(--text-tertiary)' }}>
          Workspace Agents ({enabledAgents.length} active / {agents.length} total)
        </span>
      </div>

      {error && (
        <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--accent-rose)', fontSize: '0.8rem', background: 'rgba(244,63,94,0.05)', borderRadius: '8px', border: '1px solid rgba(244,63,94,0.1)' }}>
          {error}
        </div>
      )}

      {agents.length === 0 && !error && (
        <div style={{ textAlign: 'center', padding: '24px 8px', color: '#555876', fontSize: '0.8rem', background: 'rgba(0,0,0,0.15)', borderRadius: '8px', border: '1px dashed rgba(255,255,255,0.03)' }}>
          {isLoading ? "Loading agents..." : "No agents registered."}
        </div>
      )}

      <div className="agents-grid" style={{
        display: 'grid',
        gap: '16px',
        overflowY: 'auto',
        flex: 1,
        paddingBottom: '20px'
      }}>
        {agents.map((agent) => {
          const iconData = AGENT_ICONS[agent.name] || { icon: '🔌' };
          const isActive = activeAgents.includes(agent.name);
          const isEnabled = enabledAgents.includes(agent.name);

          const cardBackground = isActive 
            ? 'rgba(0, 212, 255, 0.04)' 
            : isEnabled 
              ? 'rgba(255, 255, 255, 0.01)' 
              : 'rgba(255, 255, 255, 0.003)';
          const cardBorder = isActive 
            ? '1px solid rgba(0, 212, 255, 0.25)' 
            : isEnabled 
              ? '1px solid rgba(255, 255, 255, 0.05)' 
              : '1px solid rgba(255, 255, 255, 0.015)';
          const cardOpacity = isEnabled ? 1 : 0.45;

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
                transition: 'all 0.2s ease',
                position: 'relative',
                boxShadow: isActive ? '0 0 15px rgba(0, 212, 255, 0.05)' : 'none',
                opacity: cardOpacity
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.1rem'
                }}>
                  {iconData.icon}
                </div>
                <strong style={{ fontSize: '0.85rem', color: '#cbd5e1', textTransform: 'capitalize' }}>
                  {agent.name.replace('_', ' ')}
                </strong>
                
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
                      width: '36px',
                      height: '20px',
                      borderRadius: '10px',
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
                      width: '14px',
                      height: '14px',
                      borderRadius: '50%',
                      background: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                      transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                      transform: isEnabled ? 'translateX(18px)' : 'translateX(2px)'
                    }} />
                  </button>
                </div>
              </div>
              <p style={{ fontSize: '0.76rem', color: '#8b8fad', lineHeight: '1.45', margin: 0, flex: 1 }}>
                {agent.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
