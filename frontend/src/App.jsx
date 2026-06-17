import { useState, useRef, useEffect, useCallback } from 'react';

import ParticleBackground from './components/ParticleBackground';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import AgentPanel from './components/AgentPanel';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import TypingIndicator from './components/TypingIndicator';

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
  // State
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

  // ── Real-Time Notification Stream (SSE) ──────────────────────
  useEffect(() => {
    const eventSource = new EventSource('/api/notifications/stream');

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

    return () => {
      eventSource.close();
    };
  }, []);

  // ── Current conversation ─────────────────────────────────────
  const activeConversation = conversations.find(c => c.id === activeConversationId);
  const messages = activeConversation?.messages || [];
  
  // Get active agents in the latest JARVIS response
  const lastJarvisMessage = [...messages].reverse().find(msg => msg.role === 'jarvis');
  const activeAgents = lastJarvisMessage?.agentsUsed || [];

  // ── Health check on mount ────────────────────────────────────
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
        headers: { 'Content-Type': 'application/json' },
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
  }, [activeConversationId, createNewChat]);

  // ── Upload file ──────────────────────────────────────────────
  const handleUpload = useCallback(async (file) => {
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
  }, [activeConversationId, createNewChat]);

  // ── Delete conversation ──────────────────────────────────────
  const handleDeleteConversation = useCallback((id) => {
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
    }
  }, [activeConversationId]);

  // ── Select conversation ──────────────────────────────────────
  const handleSelectConversation = useCallback((id) => {
    setActiveConversationId(id);
    setSidebarOpen(false);
  }, []);

  // ── Render ───────────────────────────────────────────────────
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
