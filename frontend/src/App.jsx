import { useState, useRef, useEffect, useCallback } from 'react';

import ParticleBackground from './components/ParticleBackground';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import AgentsGrid from './components/AgentsGrid';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import TypingIndicator from './components/TypingIndicator';
import Login from './components/Login';
import { supabase } from './supabaseClient';
import DevPanel from './components/DevPanel';
import AgentBuilderPanel from './components/AgentBuilderPanel';
import WorkspaceExplorer from './components/WorkspaceExplorer';
import IntegrationsModal from './components/IntegrationsModal';
import TeacherStudioDashboard from './components/TeacherStudioDashboard';
import ArtifactsPanel from './components/ArtifactsPanel';

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

const PROFILE_MAP = {
  edtech_studio: {
    name: 'Bharat Adaptive Learning Studio',
    emoji: '🇮🇳',
    title: 'Welcome to Bharat Adaptive Learning Studio',
    subtitle: 'Your autonomous AI teaching workstation. Automate NCERT lesson planning, CBSE test papers, WhatsApp broadcasts, and 1-on-1 Hinglish student tutoring.',
    chips: [
      "📑 Draft NCERT Lesson Plan for Class 10 Chemistry",
      "📝 Generate CBSE Unit Test with Assertion-Reason Questions",
      "📲 Format WhatsApp Parents Notice for PTM Schedule",
      "📊 Export Student Attendance & Marksheet to Google Sheets"
    ]
  },
  developer: {
    name: 'Developer Suite',
    emoji: '💻',
    title: 'Welcome to Developer Suite Workstation',
    subtitle: 'Powered by Vibe-Coding-Claude-Fable-5 (HuggingFace) — your polyglot AI coding workstation. Generate production-ready code in 30+ languages, run sandboxed execution, debug terminal logs, and automate DevOps.',
    chips: [
      "🐍 Write a Python FastAPI REST endpoint with JWT auth",
      "⚡ Build a React TypeScript component with hooks & context",
      "🦀 Write a Rust memory-safe CLI tool with clap",
      "☕ Create a Java Spring Boot microservice with dependency injection",
      "🔷 Write a Go HTTP server with goroutines and channels",
      "🗄️ Generate SQL migrations with indexes and foreign keys",
      "🐳 Write a production Dockerfile with multi-stage build",
      "📦 Create a Bash deployment script with error handling",
      "🔧 Write a Terraform AWS ECS deployment module",
      "🧪 Generate unit tests with mocks for a JavaScript module"
    ]
  },
  cloud_devops: {
    name: 'Cloud & DevOps SRE',
    emoji: '☁️',
    title: 'Welcome to Cloud & DevOps SRE Hub',
    subtitle: 'Your autonomous SRE operations center. Validate Terraform IaC stacks, monitor Kubernetes clusters, and audit CI/CD pipelines.',
    chips: [
      "☁️ Validate Terraform AWS deployment stack",
      "⚙️ Check Kubernetes pod status and memory logs",
      "🔀 Audit GitHub Actions workflow pipeline"
    ]
  },
  creative_marketer: {
    name: 'Growth Marketing',
    emoji: '🚀',
    title: 'Welcome to Growth Marketing Studio',
    subtitle: 'Your autonomous growth marketing agency. Draft viral ad copy hooks, generate high-converting email campaigns, and analyze CAC/ROAS.',
    chips: [
      "🚀 Draft 3 high-converting Meta ad copy hooks",
      "📣 Create outbound cold email sales sequence",
      "📊 Analyze customer acquisition cost and ROAS"
    ]
  },
  financial_analyst: {
    name: 'Financial Analyst',
    emoji: '📈',
    title: 'Welcome to Financial Analyst Hub',
    subtitle: 'Your Wall Street equity research workstation. Extract fundamental stock tickers, parse P&L statements, and build financial charts.',
    chips: [
      "📈 Analyze AAPL stock fundamentals and P/E ratio",
      "📑 Draft executive summary of Q3 revenue report",
      "📊 Plot historical cryptocurrency price trends"
    ]
  }
};

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
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 900);
  const [activeTab, setActiveTab] = useState('chats'); // 'chats', 'search', 'images', 'videos', 'library'
  const [isDevPanelOpen, setIsDevPanelOpen] = useState(false);
  const [isBuilderPanelOpen, setIsBuilderPanelOpen] = useState(false);
  const [isIntegrationsOpen, setIsIntegrationsOpen] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [pendingBuilder, setPendingBuilder] = useState(null);
  const [activeArtifact, setActiveArtifact] = useState(null);

  const activeProfile = PROFILE_MAP[user?.id] || { 
    id: user?.id, 
    name: user?.user_metadata?.full_name || user?.id || 'Workspace', 
    emoji: '📂', 
    title: `Welcome to ${user?.user_metadata?.full_name || user?.id || 'Workspace'}`, 
    subtitle: "Your autonomous AI workspace. Ask me anything — I'll orchestrate specialized agents to execute your requests.", 
    chips: ["🔍 Search the web", "📊 Analyze documents", "💻 Write code"] 
  };

  const handleToast = useCallback((toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => {
      const next = [...prev, { id, ...toast }];
      return next.slice(-3);
    });
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 6000);
  }, []);

  const messagesEndRef = useRef(null);

  // Restore session from localStorage on mount & handle OAuth callbacks
  useEffect(() => {
    const savedUser = localStorage.getItem('jarvis_user');
    const savedToken = localStorage.getItem('jarvis_token');
    if (savedUser && savedToken) {
      setUser(JSON.parse(savedUser));
      setSessionToken(savedToken);
    }

    // Check for Google OAuth Callback URL parameters
    const params = new URLSearchParams(window.location.search);
    const provider = params.get('connected_provider');
    const email = params.get('email');
    if (provider && email) {
      handleToast({ level: 'success', title: 'Google Workspace OAuth Verified!', message: `Authenticated and synced with ${email}.` });
      setIsIntegrationsOpen(true);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [handleToast]);

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
      const isLocal = user.email && user.email.endsWith('@local.jarvis');
      const storageKey = isLocal ? 'jarvis_conversations_local' : `jarvis_conversations_${user.id}`;
      const savedConvs = localStorage.getItem(storageKey);
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

    const isLocal = user.email && user.email.endsWith('@local.jarvis');
    const storageKey = isLocal ? 'jarvis_conversations_local' : `jarvis_conversations_${user.id}`;
    if (conversations.length > 0) {
      const metadata = conversations.map(c => ({
        id: c.id,
        title: c.title,
        time: c.time,
        createdAt: c.createdAt,
        messages: [] // Empty messages to fetch dynamically on load/click
      }));
      localStorage.setItem(storageKey, JSON.stringify(metadata));
    } else {
      localStorage.removeItem(storageKey);
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
    
    const isCustomUser = !['developer', 'analyst', 'designer', 'manager', 'guest', 'cloud_devops', 'financial_analyst', 'cybersec_auditor', 'healthcare_researcher', 'creative_marketer', 'legal_ops'].includes(user.id);
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

  const [currentStep, setCurrentStep] = useState(null);

  // ── Real-Time Notification Stream (SSE) ──────────────────────
  useEffect(() => {
    if (!sessionToken) return;

    const eventSource = new EventSource(`/api/notifications/stream?token=${encodeURIComponent(sessionToken)}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'step_progress' || data.agent) {
          setCurrentStep(data);
        } else {
          handleToast(data);
        }
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
  }, [sessionToken, handleToast]);

  // ── Current conversation ─────────────────────────────────────
  const activeConversation = conversations.find(c => c.id === activeConversationId);
  const messages = activeConversation?.messages || [];
  
  // Get active agents in the latest JARVIS response
  const lastJarvisMessage = [...messages].reverse().find(msg => msg.role === 'jarvis' || msg.role === 'assistant');
  const activeAgents = lastJarvisMessage?.agentsUsed || [];

  const checkHealth = useCallback(async () => {
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
  }, []);

  // ── Health check on mount / interval ──────────────────────────
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

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
    if (window.innerWidth <= 900) {
      setSidebarOpen(false);
    }
    return newConv.id;
  }, []);

  // ── Send message ─────────────────────────────────────────────
  const handleSend = useCallback(async (query, isRetry = false, retryMsgId = null) => {
    if (!sessionToken) return;
    let convId = activeConversationId;

    // Auto-create conversation if none active
    if (!convId) {
      convId = createNewChat();
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    if (!isRetry) {
      const userMessage = {
        id: generateId(),
        role: 'user',
        content: query,
        timestamp: new Date().toISOString(),
      };

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
    }

    setActiveConversationId(convId);
    setIsLoading(true);

    // Placeholder streaming message or update previous failed message
    const streamingMsgId = retryMsgId || generateId();
    const streamingMessage = {
      id: streamingMsgId,
      role: 'jarvis',
      content: '',
      agentsUsed: [],
      timestamp: new Date().toISOString(),
      isStreaming: true,
      queryRef: query // Store original query string for manual retry triggers
    };

    if (!isRetry) {
      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return { ...c, messages: [...c.messages, streamingMessage] };
        }
        return c;
      }));
    } else {
      setConversations(prev => prev.map(c => {
        if (c.id === convId) {
          return {
            ...c,
            messages: c.messages.map(m => m.id === retryMsgId ? streamingMessage : m)
          };
        }
        return c;
      }));
    }

    // Helper function for fetching stream with backoff retry logic
    const fetchWithBackoff = async (url, options, maxRetries = 3, initialDelay = 1000) => {
      let delay = initialDelay;
      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          const response = await fetch(url, options);
          if (response.ok) return response;
          
          // Only retry on transient codes (e.g. 502, 503, 504, 429)
          if (response.status === 429 || (response.status >= 502 && response.status <= 504)) {
            if (attempt === maxRetries) throw new Error(`Server returned error (${response.status})`);
            logger.warn(`Fetch attempt ${attempt} failed with status ${response.status}. Retrying in ${delay}ms...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2; // exponential increase
            continue;
          }
          const errorData = await response.json().catch(() => null);
          throw new Error(errorData?.detail || `Server error (${response.status})`);
        } catch (error) {
          if (attempt === maxRetries) throw error;
          await new Promise(resolve => setTimeout(resolve, delay));
          delay *= 2;
        }
      }
    };

    try {
      const response = await fetchWithBackoff('/api/query/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ query, session_id: convId }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullContent = '';
      let agentsUsed = [];

      const updateStreamingMsg = (content, agents, step, done) => {
        setConversations(prev => prev.map(c => {
          if (c.id !== convId) return c;
          return {
            ...c,
            messages: c.messages.map(m => {
              if (m.id !== streamingMsgId) return m;
              return {
                ...m,
                content: content,
                agentsUsed: agents,
                currentStep: step || null,
                isStreaming: !done,
              };
            }),
          };
        }));
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event;
          try { event = JSON.parse(raw); } catch { continue; }

          if (event.type === 'step_start') {
            setCurrentStep({ agent: event.agent, thought: event.thought, step: event.step });
            updateStreamingMsg(fullContent, agentsUsed, `Running ${event.agent}...`, false);

          } else if (event.type === 'agent_result') {
            agentsUsed = [...new Set([...agentsUsed, event.agent])];

          } else if (event.type === 'synthesis_chunk') {
            fullContent += event.chunk;
            updateStreamingMsg(fullContent, agentsUsed, null, false);

          } else if (event.type === 'done') {
            agentsUsed = event.agents_used || agentsUsed;
            updateStreamingMsg(fullContent, agentsUsed, null, true);

          } else if (event.type === 'needs_confirmation') {
            updateStreamingMsg(event.message, agentsUsed, null, true);
            setPendingBuilder({ query, session_id: convId });

          } else if (event.type === 'error') {
            fullContent = `**Error:** ${event.detail}`;
            updateStreamingMsg(fullContent, agentsUsed, null, true);

          } else if (event.type === 'stream_end') {
            // Final clean-up: mark done
            updateStreamingMsg(fullContent || 'No response received.', agentsUsed, null, true);
          }
        }
      }

    } catch (error) {
      const errContent = `**Error:** ${error.message}\n\nMake sure the backend is running:\n\`\`\`bash\nuvicorn backend.api.server:app --reload --port 8000\n\`\`\``;
      setConversations(prev => prev.map(c => {
        if (c.id !== convId) return c;
        return {
          ...c,
          messages: c.messages.map(m =>
            m.id === streamingMsgId
              ? { ...m, content: errContent, isStreaming: false }
              : m
          ),
        };
      }));
    } finally {
      setIsLoading(false);
      setCurrentStep(null);
    }
  }, [activeConversationId, createNewChat, sessionToken]);


  const handleConfirmBuild = async (shouldBuild) => {
    if (!pendingBuilder) return;
    const { query, session_id } = pendingBuilder;
    setPendingBuilder(null);
    setIsLoading(true);

    try {
      // 1. If confirming, add a user message indicating yes
      const confirmText = shouldBuild ? "Yes, continue building the agent." : "No, abort building.";
      const confirmMsg = {
        id: generateId(),
        role: 'user',
        content: confirmText,
        timestamp: new Date().toISOString(),
      };
      
      setConversations(prev => prev.map(c => {
        if (c.id === session_id) {
          return { ...c, messages: [...c.messages, confirmMsg] };
        }
        return c;
      }));

      // 2. Query with confirm_build flag
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ query, session_id, confirm_build: shouldBuild }),
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
        if (c.id === session_id) {
          return { ...c, messages: [...c.messages, jarvisMessage] };
        }
        return c;
      }));

      checkHealth();

    } catch (error) {
      const errorMessage = {
        id: generateId(),
        role: 'jarvis',
        content: `**Error:** ${error.message}`,
        timestamp: new Date().toISOString(),
      };

      setConversations(prev => prev.map(c => {
        if (c.id === session_id) {
          return { ...c, messages: [...c.messages, errorMessage] };
        }
        return c;
      }));
    } finally {
      setIsLoading(false);
    }
  };

  // ── Upload file ──────────────────────────────────────────────
  const handleUpload = useCallback(async (file, preventRedirect = false) => {
    if (!sessionToken) return;
    setIsUploading(true);
    let convId = activeConversationId;

    if (!convId) {
      if (preventRedirect) {
        convId = "temp_upload";
      } else {
        convId = createNewChat();
        await new Promise(resolve => setTimeout(resolve, 0));
      }
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
      window.reloadWorkspaceFiles?.();

      if (convId !== "temp_upload") {
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
      } else {
        handleToast({ title: "File Uploaded", message: `"${data.filename}" uploaded and indexed successfully.`, level: "success" });
      }

    } catch (error) {
      console.error(error);
      if (convId !== "temp_upload") {
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
      } else {
        handleToast({ title: "Upload Error", message: error.message, level: "error" });
      }
    } finally {
      setIsUploading(false);
    }
  }, [activeConversationId, createNewChat, sessionToken, handleToast]);

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
    if (window.innerWidth <= 900) {
      setSidebarOpen(false);
    }

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
        {toasts?.map(toast => (
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
          sessionToken={sessionToken}
          onToast={handleToast}
          onToggleSidebar={() => setSidebarOpen(prev => !prev)}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onToggleDevPanel={() => setIsDevPanelOpen(true)}
          onToggleBuilderPanel={() => setIsBuilderPanelOpen(true)}
          onGoHome={() => {
            setActiveConversationId(null);
            setActiveTab('chats');
          }}
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
            onToggleDevPanel={() => setIsDevPanelOpen(true)}
            onToggleBuilderPanel={() => setIsBuilderPanelOpen(true)}
            activeProfile={activeProfile}
            onToggleIntegrations={() => setIsIntegrationsOpen(true)}
          />

          <div style={{ display: 'flex', flex: 1, overflow: 'hidden', width: '100%' }}>
            <div className="chat-area" style={{ 
              flex: activeArtifact ? '0 0 50%' : '1',
              padding: (activeTab === 'images' || activeTab === 'videos' || activeTab === 'library' || activeTab === 'agents') ? '24px' : undefined,
              overflowY: (activeTab === 'images' || activeTab === 'videos' || activeTab === 'library' || activeTab === 'agents') ? 'auto' : undefined,
              display: 'flex',
              flexDirection: 'column'
            }}>
              {(activeTab === 'chats' || activeTab === 'search') && (
                <>
                  {(!activeConversationId && (user?.id === 'edtech_studio' || activeProfile?.id === 'edtech_studio')) ? (
                    <TeacherStudioDashboard
                      onSend={handleSend}
                      isLoading={isLoading}
                      onUpload={handleUpload}
                      isUploading={isUploading}
                    />
                  ) : showWelcome ? (
                    <div className="welcome-container">
                      <div className="welcome-icon">{activeProfile?.emoji || '🤖'}</div>
                      <h1 className="welcome-title">{activeProfile?.title || 'Welcome to JARVIS'}</h1>
                      <p className="welcome-subtitle">
                        {activeProfile?.subtitle || "Your autonomous AI operating system. Ask me anything — I'll orchestrate specialized agents to execute your requests."}
                      </p>
                      <div className="prompt-chips">
                        {(activeProfile?.chips || [
                          "🔍 Search for the latest AI breakthroughs",
                          "📊 Analyze my uploaded documents",
                          "💻 Write a Python web scraper",
                          "📝 Summarize a research topic"
                        ]).map((prompt, i) => (
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
                      {messages.map((msg, idx) => (
                        <ChatMessage
                          key={msg.id || `msg-${idx}`}
                          role={msg.role === 'assistant' ? 'jarvis' : msg.role}
                          content={msg.content}
                          timestamp={msg.timestamp}
                          sessionToken={sessionToken}
                          onSelectArtifact={setActiveArtifact}
                          isStreaming={msg.isStreaming || false}
                          currentStep={msg.currentStep || null}
                          onRetry={() => {
                            // Find the query preceding this error message
                            const prevMessage = idx > 0 ? messages[idx - 1] : null;
                            const query = prevMessage && prevMessage.role === 'user' ? prevMessage.content : msg.queryRef;
                            if (query) {
                              handleSend(query, true, msg.id);
                            }
                          }}
                        />
                      ))}
                      {/* TypingIndicator is replaced by the streaming message bubble */}
                      {isLoading && !messages.some(m => m.isStreaming) && <TypingIndicator currentStep={currentStep} />}
                      <div ref={messagesEndRef} />
                    </div>
                  )}

                  {!((user?.id === 'edtech_studio' || activeProfile?.id === 'edtech_studio') && !activeConversationId) && (
                    <ChatInput
                      onSend={handleSend}
                      onUpload={handleUpload}
                      isLoading={isLoading}
                      isUploading={isUploading}
                      showSuggestions={false}
                    />
                  )}
                </>
              )}

              {activeTab === 'images' && (
                <WorkspaceExplorer sessionToken={sessionToken} onToast={handleToast} filterType="image" />
              )}
              {activeTab === 'videos' && (
                <WorkspaceExplorer sessionToken={sessionToken} onToast={handleToast} filterType="video" />
              )}
              {activeTab === 'library' && (
                <WorkspaceExplorer sessionToken={sessionToken} onToast={handleToast} filterType="all" />
              )}
              {activeTab === 'agents' && (
                <AgentsGrid activeAgents={activeAgents} sessionToken={sessionToken} onToast={handleToast} />
              )}
            </div>
            {activeArtifact && (
              <ArtifactsPanel artifact={activeArtifact} onClose={() => setActiveArtifact(null)} />
            )}
          </div>
        </div>
      </div>

      {isDevPanelOpen && (
        <DevPanel
          sessionToken={sessionToken}
          userId={user?.id}
          onClose={() => setIsDevPanelOpen(false)}
        />
      )}

      {isBuilderPanelOpen && (
        <AgentBuilderPanel
          sessionToken={sessionToken}
          onClose={() => setIsBuilderPanelOpen(false)}
          onAgentReloaded={checkHealth}
        />
      )}

      {pendingBuilder && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '20px'
        }}>
          <div style={{
            background: 'rgba(30, 30, 60, 0.85)',
            border: '1px solid rgba(124, 58, 237, 0.4)',
            borderRadius: '20px',
            padding: '24px',
            maxWidth: '500px',
            width: '100%',
            boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)',
            color: '#e8eaff',
            animation: 'fadeIn 0.3s ease-out'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.25rem', fontWeight: 700, color: '#00d4ff' }}>
              🔧 Create Custom Agent?
            </h3>
            <p style={{ margin: '0 0 20px 0', fontSize: '0.95rem', lineHeight: '1.5', color: '#b9bbdb' }}>
              JARVIS needs to build a new custom agent module to handle your request. This will compile, import, and validate a new Python tool in the background, which typically takes 15-30 seconds.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => handleConfirmBuild(false)}
                style={{
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  color: '#f43f5e',
                  padding: '10px 18px',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '600',
                  transition: 'all 0.2s'
                }}
              >
                Abort
              </button>
              <button
                onClick={() => handleConfirmBuild(true)}
                style={{
                  background: 'linear-gradient(135deg, #7c3aed, #00d4ff)',
                  border: 'none',
                  color: '#fff',
                  padding: '10px 20px',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '600',
                  boxShadow: '0 4px 15px rgba(124, 58, 237, 0.3)',
                  transition: 'all 0.2s'
                }}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      <IntegrationsModal 
        isOpen={isIntegrationsOpen} 
        onClose={() => setIsIntegrationsOpen(false)} 
        onToast={handleToast} 
      />
    </>
  );
}
