export default function Header({ isOnline, agentCount, version, sidebarOpen, onToggleSidebar, user, onLogout, onDeleteActiveWorkspace, onToggleDevPanel, onToggleBuilderPanel, activeProfile, onToggleIntegrations }) {
  return (
    <header className="header" id="jarvis-header">
      <div className="header-left">
        <span style={{
          fontSize: '0.85rem',
          fontWeight: 800,
          letterSpacing: '1.5px',
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textTransform: 'uppercase'
        }}>
          JARVIS OS
        </span>
      </div>

      <div className="header-center">
        {activeProfile && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '4px 14px',
            background: 'rgba(0, 212, 255, 0.08)',
            border: '1px solid rgba(0, 212, 255, 0.25)',
            borderRadius: '99px',
            color: '#00d4ff',
            fontSize: '0.76rem',
            fontWeight: 800,
            letterSpacing: '1px',
            textTransform: 'uppercase',
            boxShadow: '0 0 12px rgba(0, 212, 255, 0.15)'
          }}>
            <span>{activeProfile.emoji || '📂'}</span>
            <span>{activeProfile.name || activeProfile.id}</span>
          </div>
        )}
      </div>

      <div className="header-right">
        {user && (
          <div className="header-user-section">
            <div className="user-profile-pill">
              <span className="user-avatar-icon">👤</span>
              <span className="user-name">{user.user_metadata?.full_name || user.email?.split('@')[0]}</span>
            </div>

            <div className="user-actions">
              <button
                className="user-action-btn"
                onClick={onToggleIntegrations}
                style={{
                  background: 'rgba(0, 212, 255, 0.12)',
                  border: '1px solid rgba(0, 212, 255, 0.3)',
                  color: '#00d4ff',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px'
                }}
                title="Manage Third-Party Integrations & OAuth"
              >
                <span>🔌</span> Integrations
              </button>
              <button
                className="user-action-btn btn-logout"
                onClick={onLogout}
                title="Sign Out"
              >
                Sign Out
              </button>
              <button
                className="user-action-btn btn-delete-ws"
                onClick={onDeleteActiveWorkspace}
                title="Delete active workspace and all its data"
              >
                Delete Workspace
              </button>
            </div>
          </div>
        )}

        <div className="header-status-badges">
          {!isOnline && (
            <div className="status-badge offline">
              <span className="status-dot" />
              <span className="badge-text">Offline</span>
            </div>
          )}
        </div>
      </div>
      {isOnline && <div className="header-active-line" />}
    </header>
  );
}
