export default function Header({ isOnline, agentCount, version, sidebarOpen, onToggleSidebar, voiceEnabled, onToggleVoice }) {
  return (
    <header className="header" id="jarvis-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? '✕' : '☰'}
        </button>

        <div className="header-brand">
          <div className="header-logo">
            <div className="header-logo-ring" />
            <div className="header-logo-core" />
          </div>
          <div>
            <div className="header-title">JARVIS</div>
            <div className="header-subtitle">Autonomous AI Operating System</div>
          </div>
        </div>
      </div>

      <div className="header-status">
        <button
          className="voice-toggle-btn"
          onClick={onToggleVoice}
          title={voiceEnabled ? "Mute Voice Read-Back" : "Enable Voice Read-Back"}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1.2rem',
            padding: '4px 8px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: voiceEnabled ? 'var(--accent-cyan)' : 'var(--text-tertiary)',
            transition: 'color var(--transition-fast)'
          }}
        >
          {voiceEnabled ? '🔊' : '🔇'}
        </button>

        <div className={`status-badge ${isOnline ? '' : 'offline'}`}>
          <span className="status-dot" />
          {isOnline ? 'System Online' : 'Offline'}
        </div>
        {agentCount > 0 && (
          <div className="status-badge">
            <span style={{ fontSize: '0.7rem' }}>⚡</span>
            {agentCount} Agents
          </div>
        )}
        <span className="version-badge">v{version || '1.0.0'}</span>
      </div>
    </header>
  );
}
