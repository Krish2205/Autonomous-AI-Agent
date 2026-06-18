import { useState, useRef, useEffect, useCallback } from 'react';

import ParticleBackground from './components/ParticleBackground';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import AgentPanel from './components/AgentPanel';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import TypingIndicator from './components/TypingIndicator';
import Login from './components/Login';
import { supabase } from './supabaseClient';

// ── Helpers ────────────────────────────────────────────────────────
function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 8);
}

function truncateTitle(text, maxLen = 40) {
  if (!text) return 'New Chat';
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── Main App ───────────────────────────────────────────────────────
export default function App() {
  // ── Authentication State ─────────────────────────────────────────
  const [user, setUser] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [hasLoaded, setHasLoaded] = useState(false);

  // ── UI / Chat State ──────────────────────────────────────────────
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [agentCount, setAgentCount] = useState(0);
  const [version, setVersion] = useState('1.0.0');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toasts, setToasts] = useState([]);

  const messagesEndRef = useRef(null);

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('jarvis_user');
    const savedToken = localStorage.getItem('jarvis_token');
    if (savedUser && savedToken) {
      setUser(JSON.parse(savedUser));
      setSessionToken(savedToken);
    }
  }, []);

  // Listen to Supabase auth state changes if active
  useEffect(() => {
    if (!supabase) return;

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        handleAuthSuccess(session.user, session.access_token);
      } else if (event === 'SIGNED_OUT') {
        handleLogout();
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // Load user conversation list from localStorage
  useEffect(() => {
    setHasLoaded(false);
    if (user) {
      const savedConvs = localStorage.getItem(`jarvis_conversations_${user.id}`);
      if (savedConvs) {
        try {
          setConversations(JSON.parse(savedConvs));
        } catch (e) {
          console.error("Failed to parse conversations:", e);
          setConversations([]);
        }
      } else {
        setConversations([]);
      }
      setHasLoaded(true);
    } else {
      setConversations([]);
    }
  }, [user]);

  // Sync conversation list metadata to localStorage
  useEffect(() => {
    if (!user || !hasLoaded) return;

    if (conversations.length > 0) {
      const metadata = conversations.map(c => ({
        id: c.id,
        title: c.title,
        time: c.time,
        createdAt: c.createdAt,
        messages: [] // Empty messages to fetch dynamically on load/click
      }));
      localStorage.setItem(`jarvis_conversations_${user.id}`, JSON.stringify(metadata));
    } else {
      localStorage.removeItem(`jarvis_conversations_${user.id}`);
    }
  }, [conversations, user, hasLoaded]);

  const handleAuthSuccess = (authUser, token) => {
    setUser(authUser);
    setSessionToken(token);
    localStorage.setItem('jarvis_user', JSON.stringify(authUser));
    localStorage.setItem('jarvis_token', token);
  };

  const handleLogout = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setSessionToken(null);
    localStorage.removeItem('jarvis_user');
    localStorage.removeItem('jarvis_token');
    setConversations([]);
    setActiveConversationId(null);
    setHasLoaded(false);
  }, []);

  const handleDeleteActiveWorkspace = useCallback(async () => {
    if (!user) return;
    
    const isCustomUser = !['developer', 'designer', 'manager', 'guest'].includes(user.id);
    const workspaceName = user.user_metadata?.full_name || user.id;
    
    const message = isCustomUser 
      ? `Are you sure you want to delete the custom workspace "${workspaceName}" and ALL of its conversation history, uploaded files, and databases? This action is permanent.`
      : `Are you sure you want to clear ALL backend databases, files, and conversation history for the default workspace "${workspaceName}"? This action cannot be undone.`;

    const confirmed = window.confirm(message);
    if (!confirmed) return;

    try {
      // 1. Call backend to delete backend data
      const res = await fetch(`/api/workspace/${user.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        }
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to delete backend data (status: ${res.status})`);
      }

      // 2. Clear frontend local storage for conversations of this workspace
      localStorage.removeItem(`jarvis_conversations_${user.id}`);

      // 3. If it is a custom workspace, remove it from list of custom workspaces
      if (isCustomUser) {
        const savedWorkspaces = localStorage.getItem('jarvis_custom_workspaces');
        if (savedWorkspaces) {
          try {
            const list = JSON.parse(savedWorkspaces);
            const updated = list.filter(w => w.id !== user.id);
            localStorage.setItem('jarvis_custom_workspaces', JSON.stringify(updated));
          } catch (e) {
            console.error("Failed to update custom workspaces list:", e);
          }
        }
      }

      // 4. Trigger standard logout to reset UI state
      await handleLogout();
      
      alert(`Workspace "${workspaceName}" has been successfully deleted.`);
    } catch (err) {
      alert(`Error deleting workspace: ${err.message}`);
    }
  }, [user, sessionToken, handleLogout]);

  // ── Real-Time Notification Stream (SSE) ──────────────────────
  useEffect(() => {
    if (!sessionToken) return;

    const eventSource = new EventSource(`/api/notifications/stream?token=${encodeURIComponent(sessionToken)}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const id = Math.random().toString(36).substring(2, 9);
        setToasts(prev => [...prev, { id, ...data }]);

        // Auto-dismiss after 6 seconds
        setTimeout(() => {
          setToasts(prev => prev.filter(t => t.id !== id));
        }, 6000);
      } catch (err) {
        console.error("Failed to parse incoming notification:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE connection error:", err);
    };

    return () => {
      eventSource.close();
    };
  }, [sessionToken]);

  // ── Current conversation ─────────────────────────────────────
  const activeConversation = conversations.find(c => c.id === activeConversationId);
  const messages = activeConversation?.messages || [];
  
  // Get active agents in the latest JARVIS response
  const lastJarvisMessage = [...messages].reverse().find(msg => msg.role === 'jarvis');
  const activeAgents = lastJarvisMessage?.agentsUsed || [];

  // ── Health check on mount / interval ──────────────────────────
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          setIsOnline(true);
          setAgentCount(data.agents_registered || 0);
          setVersion(data.version || '1.0.0');
        } else {
          setIsOnline(false);
        }
      } catch {
        setIsOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // ── Auto-scroll ──────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Create new conversation ──────────────────────────────────
  const createNewChat = useCallback(() => {
    const newConv = {
      id: generateId(),
      title: 'New Chat',
      time: formatTime(new Date()),
      messages: [],
      createdAt: Date.now(),
    };
    setConversations(prev => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    setSidebarOpen(false);
    return newConv.id;
  }, []);

  // ── Send message ─────────────────────────────────────────────
  const handleSend = useCallback(async (query) => {
    if (!sessionToken) return;
    let convId = activeConversationId;

    // Auto-create conversation if none active
    if (!convId) {
      convId = createNewChat();
      // Need to wait for state to settle
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    const userMessage = {
      id: generateId(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    // Add user message and update title
    setConversations(prev => prev.map(c => {
      if (c.id === convId) {
        const isFirstMessage = c.messages.length === 0;
        return {
          ...c,
          messages: [...c.messages, userMessage],
          title: isFirstMessage ? truncateTitle(query) : c.title,
          time: formatTime(new Date()),
        };
      }
      return c;
    }));

    // Set active if needed (for auto-created chats)
    setActiveConversationId(convId);
    setIsLoading(true);

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ query, session_id: convId }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Server error (${response.status})`);
      }

      const data = await response.json();

      const jarvisMessage = {
        id: generateId(),
        role: 'jarvis',
        content: data.response || 'No response received.',
        agentsUsed: data.agents_used || [],
        timestamp: new Date().toISOString(),
      };

      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return { ...c, messages: [...c.messages, jarvisMessage] };
        }
        return c;
      }));

    } catch (error) {
      const errorMessage = {
        id: generateId(),
        role: 'jarvis',
        content: `**Error:** ${error.message}\n\nMake sure the backend is running:\n\`\`\`bash\nuvicorn backend.api.server:app --reload --port 8000\n\`\`\``,
        timestamp: new Date().toISOString(),
      };

      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return { ...c, messages: [...c.messages, errorMessage] };
        }
        return c;
      }));
    } finally {
      setIsLoading(false);
    }
  }, [activeConversationId, createNewChat, sessionToken]);

  // ── Upload file ──────────────────────────────────────────────
  const handleUpload = useCallback(async (file) => {
    if (!sessionToken) return;
    setIsUploading(true);
    let convId = activeConversationId;

    if (!convId) {
      convId = createNewChat();
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`/api/upload?session_id=${convId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionToken}`
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Upload failed (${response.status})`);
      }

      const data = await response.json();

      const systemMessage = {
        id: generateId(),
        role: 'jarvis',
        content: `📁 **File Uploaded Successfully:** \`${data.filename}\` has been parsed and indexed. You can now ask questions about its content!`,
        timestamp: new Date().toISOString(),
      };

      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return { ...c, messages: [...c.messages, systemMessage] };
        }
        return c;
      }));

    } catch (error) {
      const errorMessage = {
        id: generateId(),
        role: 'jarvis',
        content: `❌ **Upload Error:** ${error.message}`,
        timestamp: new Date().toISOString(),
      };

      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return { ...c, messages: [...c.messages, errorMessage] };
        }
        return c;
      }));
    } finally {
      setIsUploading(false);
    }
  }, [activeConversationId, createNewChat, sessionToken]);

  // ── Delete conversation ──────────────────────────────────────
  const handleDeleteConversation = useCallback(async (id) => {
    if (sessionToken) {
      try {
        await fetch(`/api/session/${id}/clear`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
      } catch (e) {
        console.error("Failed to clear session from backend:", e);
      }
    }
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
    }
  }, [activeConversationId, sessionToken]);

  // ── Select conversation & fetch history ──────────────────────
  const handleSelectConversation = useCallback(async (id) => {
    setActiveConversationId(id);
    setSidebarOpen(false);

    // Fetch message history from backend dynamically
    if (sessionToken) {
      try {
        const response = await fetch(`/api/session/${id}/history`, {
          headers: { 'Authorization': `Bearer ${sessionToken}` }
        });
        if (response.ok) {
          const data = await response.json();
          if (data.history) {
            setConversations(prev => prev.map(c => {
              if (c.id === id) {
                return { ...c, messages: data.history };
              }
              return c;
            }));
          }
        }
      } catch (e) {
        console.error("Failed to load conversation history:", e);
      }
    }
  }, [sessionToken]);

  // If user is not logged in, render the login interface
  if (!sessionToken) {
    return <Login onAuthSuccess={handleAuthSuccess} />;
  }

  const showWelcome = !activeConversation || messages.length === 0;

  return (
    <>
      <ParticleBackground />

      {/* Floating Toast Notification Container */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast-card ${toast.level}`}>
            <div className="toast-header">
              <span className="toast-icon">
                {toast.level === 'success' && '✅'}
                {toast.level === 'warning' && '⚠️'}
                {toast.level === 'error' && '🚨'}
                {toast.level === 'info' && 'ℹ️'}
              </span>
              <strong className="toast-title">{toast.title}</strong>
              <button
                className="toast-close"
                onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
              >
                &times;
              </button>
            </div>
            <div className="toast-body">{toast.message}</div>
          </div>
        ))}
      </div>

      <div className="app-layout">
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewChat={createNewChat}
          onDeleteConversation={handleDeleteConversation}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <div className="main-area">
          <Header
            isOnline={isOnline}
            agentCount={agentCount}
            version={version}
            sidebarOpen={sidebarOpen}
            onToggleSidebar={() => setSidebarOpen(prev => !prev)}
            user={user}
            onLogout={handleLogout}
            onDeleteActiveWorkspace={handleDeleteActiveWorkspace}
          />

          <div className="chat-area">
            {showWelcome ? (
              <div className="welcome-container">
                <div className="welcome-icon">🤖</div>
                <h1 className="welcome-title">Welcome to JARVIS</h1>
                <p className="welcome-subtitle">
                  Your autonomous AI operating system. Ask me anything — I'll orchestrate
                  specialized agents to search the web, analyze documents, write code,
                  manage emails, and more.
                </p>
                <div className="prompt-chips">
                  {[
                    "🔍 Search for the latest AI breakthroughs",
                    "📊 Analyze my uploaded documents",
                    "💻 Write a Python web scraper",
                    "📝 Summarize a research topic",
                    "📧 Check my email inbox",
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      className="prompt-chip"
                      onClick={() => handleSend(prompt.replace(/^[^\s]+\s/, ''))}
                      disabled={isLoading}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="chat-messages" id="chat-messages">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    timestamp={msg.timestamp}
                  />
                ))}
                {isLoading && <TypingIndicator />}
                <div ref={messagesEndRef} />
              </div>
            )}

            <ChatInput
              onSend={handleSend}
              onUpload={handleUpload}
              isLoading={isLoading}
              isUploading={isUploading}
              showSuggestions={false}
            />
          </div>
        </div>

        <AgentPanel activeAgents={activeAgents} />
      </div>
    </>
  );
}
