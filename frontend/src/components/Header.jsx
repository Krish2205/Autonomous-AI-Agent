export default function Header({ isOnline, agentCount, version, sidebarOpen, onToggleSidebar, user, onLogout, onDeleteActiveWorkspace }) {
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
        {user && (
          <div className="status-badge" style={{ background: 'rgba(124, 58, 237, 0.1)', borderColor: 'rgba(124, 58, 237, 0.25)', color: '#a78bfa', gap: '10px' }}>
            <span style={{ fontSize: '0.9rem' }}>👤</span>
            <span>{user.user_metadata?.full_name || user.email?.split('@')[0]}</span>
            <button 
              onClick={onLogout}
              style={{
                background: 'none',
                border: 'none',
                color: '#f43f5e',
                cursor: 'pointer',
                fontWeight: 'bold',
                marginLeft: '8px',
                fontSize: '0.75rem',
                textTransform: 'uppercase',
                letterSpacing: '1px'
              }}
              title="Sign Out"
            >
              Sign Out
            </button>
            <button 
              onClick={onDeleteActiveWorkspace}
              style={{
                background: 'none',
                border: 'none',
                color: '#ff4a6b',
                cursor: 'pointer',
                fontWeight: 'bold',
                marginLeft: '12px',
                fontSize: '0.75rem',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                borderLeft: '1px solid rgba(255, 255, 255, 0.15)',
                paddingLeft: '12px'
              }}
              title="Delete active workspace and all its data"
            >
              Delete Workspace
            </button>
          </div>
        )}
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
