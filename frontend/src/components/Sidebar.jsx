import { useState } from 'react';

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
  onToggleSidebar,
  activeTab,
  setActiveTab,
  onToggleDevPanel,
  onToggleBuilderPanel,
}) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = conversations.filter(c => 
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
      />

      <aside className={`sidebar ${isOpen ? 'open' : ''}`} id="sidebar">
        <div className="sidebar-top-controls" style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: isOpen ? 'space-between' : 'center', 
          padding: '10px 16px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          minHeight: '52px',
          flexShrink: 0
        }}>
          {isOpen && (
            <div className="sidebar-brand-mini" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="header-logo-core" style={{ width: '12px', height: '12px', animation: 'none' }} />
              <span style={{ fontSize: '0.9rem', fontWeight: 800, letterSpacing: '2px', background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>JARVIS</span>
            </div>
          )}
          <button
            className="sidebar-toggle"
            onClick={onToggleSidebar}
            aria-label="Toggle sidebar"
            title={isOpen ? "Collapse sidebar" : "Expand sidebar"}
            style={{ width: '32px', height: '32px' }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '18px', height: '18px' }}>
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
          </button>
        </div>

        {/* Menu Navigation Options */}
        <div className="sidebar-nav-menu" style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: '2px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', flexShrink: 0 }}>
          <button 
            className="nav-menu-item"
            onClick={() => {
              onNewChat();
              setActiveTab('chats');
            }}
            title="New Chat"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
                <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
            </span>
            {isOpen && <span className="nav-menu-text">New Chat</span>}
          </button>

          <button 
            className={`nav-menu-item ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
            title="Search Chats"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🔍</span>
            {isOpen && <span className="nav-menu-text">Search Chats</span>}
          </button>

          <button 
            className={`nav-menu-item ${activeTab === 'images' ? 'active' : ''}`}
            onClick={() => setActiveTab('images')}
            title="Images"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🖼️</span>
            {isOpen && <span className="nav-menu-text">Images</span>}
          </button>

          <button 
            className={`nav-menu-item ${activeTab === 'videos' ? 'active' : ''}`}
            onClick={() => setActiveTab('videos')}
            title="Videos"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🎬</span>
            {isOpen && <span className="nav-menu-text">Videos</span>}
          </button>

          <button 
            className={`nav-menu-item ${activeTab === 'library' ? 'active' : ''}`}
            onClick={() => setActiveTab('library')}
            title="Library"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🗂️</span>
            {isOpen && <span className="nav-menu-text">Library</span>}
          </button>

          <button 
            className={`nav-menu-item ${activeTab === 'agents' ? 'active' : ''}`}
            onClick={() => setActiveTab('agents')}
            title="Agents"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🤖</span>
            {isOpen && <span className="nav-menu-text">Agents</span>}
          </button>
        </div>

        {/* Tab Content Section */}
        <div className="sidebar-tab-content" style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column' }}>
          
          {activeTab === 'search' && isOpen && (
            <div style={{ marginBottom: '16px', padding: '0 4px' }}>
              <input
                type="text"
                placeholder="Search recent conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  color: 'var(--text-primary)',
                  fontSize: '0.82rem',
                  outline: 'none',
                  transition: 'border 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = 'rgba(0, 212, 255, 0.3)'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.05)'}
              />
            </div>
          )}

          <div className="sidebar-conversations" style={{ padding: 0 }}>
            {filteredConversations.length > 0 && isOpen && (
              <div className="sidebar-label" style={{ padding: '0 4px 8px 4px' }}>Conversations</div>
            )}

            {filteredConversations.length === 0 ? (
              isOpen && (
                <div className="sidebar-empty">
                  No conversations found.
                </div>
              )
            ) : (
              filteredConversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${conv.id === activeConversationId && (activeTab === 'chats' || activeTab === 'search') ? 'active' : ''}`}
                  onClick={() => {
                    onSelectConversation(conv.id);
                    setActiveTab('chats');
                  }}
                  id={`conv-${conv.id}`}
                  title={!isOpen ? conv.title : undefined}
                  style={{ margin: '0 0 6px 0' }}
                >
                  <span className="conversation-icon">💬</span>
                  {isOpen && (
                    <>
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
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Sidebar Footer/Bottom Action */}
        <div className="sidebar-footer" style={{ 
          padding: '8px 12px', 
          borderTop: '1px solid rgba(255, 255, 255, 0.05)', 
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <button 
            className="nav-menu-item"
            onClick={onToggleBuilderPanel}
            title="Open Meta-Agent Builder"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🛠️</span>
            {isOpen && <span className="nav-menu-text">Builder</span>}
          </button>

          <button 
            className="nav-menu-item"
            onClick={onToggleDevPanel}
            title="Open Developer & Webhook Hub"
            style={{ background: 'transparent', border: 'none', textAlign: 'left', width: '100%' }}
          >
            <span className="nav-menu-icon" style={{ fontSize: '1.1rem', marginRight: isOpen ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>⚙️</span>
            {isOpen && <span className="nav-menu-text">Dev Hub</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
