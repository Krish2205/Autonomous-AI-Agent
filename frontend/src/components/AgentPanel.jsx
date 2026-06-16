import { useState, useEffect } from 'react';

const AGENT_ICONS = {
  search: { icon: '🔍', className: 'search' },
  code: { icon: '💻', className: 'code' },
  analyse: { icon: '📊', className: 'analyse' },
  summary: { icon: '📝', className: 'summary' },
  email: { icon: '📧', className: 'email' },
  database: { icon: '🗄️', className: 'database' },
  scraper: { icon: '🌐', className: 'scraper' },
};

export default function AgentPanel({ activeAgents = [] }) {
  const [agents, setAgents] = useState([]);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAgents();
    fetchHealth();

    // Refresh health every 30s
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      const res = await fetch('/api/agents');
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
        setError(null);
      }
    } catch (err) {
      setError('Cannot reach backend');
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch {
      setHealth(null);
    }
  };

  return (
    <aside className="agent-panel" id="agent-panel">
      <div className="agent-panel-header">
        <span className="agent-panel-title">Agent Registry</span>
        <span className="agent-panel-count">{agents.length}</span>
      </div>

      <div className="agent-list">
        {error && (
          <div className="error-message">{error}</div>
        )}

        {agents.length === 0 && !error && (
          <div style={{ padding: '16px', color: 'var(--text-tertiary)', fontSize: '0.8rem', textAlign: 'center' }}>
            Loading agents...
          </div>
        )}

        {agents.map((agent) => {
          const iconData = AGENT_ICONS[agent.name] || { icon: '🔌', className: '' };
          const isActive = activeAgents.includes(agent.name);
          return (
            <div className={`agent-card ${isActive ? 'active-run' : ''}`} key={agent.name} id={`agent-${agent.name}`}>
              <div className="agent-card-header">
                <div className={`agent-icon ${iconData.className}`}>
                  {iconData.icon}
                </div>
                <span className="agent-name">{agent.name}</span>
                {isActive ? (
                  <span className="agent-active-badge">Active</span>
                ) : (
                  <span className="agent-status-dot" title="Online" />
                )}
              </div>
              <div className="agent-description">{agent.description}</div>
            </div>
          );
        })}
      </div>

      {health && (
        <div className="system-health">
          <div className="health-title">System Health</div>
          <div className="health-grid">
            <div className="health-item">
              <div className="health-value">{health.agents_registered || 0}</div>
              <div className="health-label">Agents</div>
            </div>
            <div className="health-item">
              <div className="health-value" style={{ color: health.status === 'ok' ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                {health.status === 'ok' ? '✓' : '✕'}
              </div>
              <div className="health-label">Status</div>
            </div>
            <div className="health-item" style={{ gridColumn: '1 / -1' }}>
              <div className="health-value" style={{ fontSize: '0.9rem' }}>{health.version || 'N/A'}</div>
              <div className="health-label">Version</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
