export default function Header({ isOnline, agentCount, version, sidebarOpen, onToggleSidebar, user, onLogout, onDeleteActiveWorkspace, onToggleDevPanel, onToggleBuilderPanel }) {
  return (
    <header className="header" id="jarvis-header">
      <div className="header-left">
        <span style={{
          fontSize: '0.9rem',
          fontWeight: 800,
          letterSpacing: '2px',
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          textTransform: 'uppercase'
        }}>
          Multi-Agent AI System
        </span>
      </div>

      <div className="header-center">
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
