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
  voice: { icon: '🎙️' }
};

export default function AgentsGrid({ activeAgents = [] }) {
  const [agents, setAgents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAgents = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/agents');
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
        setError(null);
      }
    } catch (err) {
      setError('Cannot reach backend');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  return (
    <div className="workspace-explorer-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', padding: '0 4px' }}>
        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 700, color: 'var(--text-tertiary)' }}>
          Active System Agents ({agents.length})
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
          return (
            <div
              key={agent.name}
              className={`agent-card-grid-item ${isActive ? 'active-run' : ''}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                padding: '20px',
                background: isActive ? 'rgba(0, 212, 255, 0.04)' : 'rgba(255, 255, 255, 0.01)',
                border: isActive ? '1px solid rgba(0, 212, 255, 0.25)' : '1px solid rgba(255, 255, 255, 0.03)',
                borderRadius: '12px',
                transition: 'all 0.2s ease',
                position: 'relative',
                boxShadow: isActive ? '0 0 15px rgba(0, 212, 255, 0.05)' : 'none'
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
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: isActive ? 'var(--accent-cyan)' : 'var(--accent-emerald)',
                    boxShadow: isActive ? '0 0 8px var(--accent-cyan)' : '0 0 8px var(--accent-emerald)',
                    marginLeft: 'auto'
                  }}
                  title={isActive ? "Running task" : "Idle (Online)"}
                />
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
