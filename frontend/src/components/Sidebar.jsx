import WorkspaceExplorer from './WorkspaceExplorer';

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  isOpen,
  onClose,
  sessionToken,
  onToast,
}) {
  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
      />

      <aside className={`sidebar ${isOpen ? 'open' : ''}`} id="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={onNewChat} id="new-chat-btn">
            <span>＋</span>
            New Chat
          </button>
        </div>

        <div className="sidebar-conversations">
          {conversations.length > 0 && (
            <div className="sidebar-label">Conversations</div>
          )}

          {conversations.length === 0 ? (
            <div className="sidebar-empty">
              No conversations yet.<br />
              Start a new chat to begin.
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conversation-item ${conv.id === activeConversationId ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
                id={`conv-${conv.id}`}
              >
                <span className="conversation-icon">💬</span>
                <div className="conversation-text">
                  <div className="conversation-title">{conv.title}</div>
                  <div className="conversation-time">{conv.time}</div>
                </div>
                <button
                  className="conversation-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  title="Delete conversation"
                  aria-label="Delete conversation"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer-explorer" style={{ padding: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.05)', overflowY: 'auto' }}>
          <WorkspaceExplorer sessionToken={sessionToken} onToast={onToast} />
        </div>
      </aside>
    </>
  );
}
