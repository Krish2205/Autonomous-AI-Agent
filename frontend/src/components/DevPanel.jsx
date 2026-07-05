import { useState, useEffect, useRef } from 'react';

// ── Language Configuration ─────────────────────────────────────────────────
const LANGUAGE_GROUPS = {
  'Interpreted': [
    { id: 'python', label: 'Python', icon: '🐍', color: '#3776AB' },
    { id: 'javascript', label: 'JavaScript', icon: '⚡', color: '#F7DF1E' },
    { id: 'typescript', label: 'TypeScript', icon: '🔷', color: '#3178C6' },
    { id: 'ruby', label: 'Ruby', icon: '💎', color: '#CC342D' },
    { id: 'php', label: 'PHP', icon: '🐘', color: '#777BB4' },
    { id: 'go', label: 'Go', icon: '🐹', color: '#00ADD8' },
    { id: 'dart', label: 'Dart', icon: '🎯', color: '#0175C2' },
    { id: 'lua', label: 'Lua', icon: '🌙', color: '#2C2D72' },
    { id: 'r', label: 'R', icon: '📊', color: '#276DC3' },
    { id: 'julia', label: 'Julia', icon: '🔬', color: '#9558B2' },
  ],
  'Compiled': [
    { id: 'c', label: 'C', icon: '⚙️', color: '#A8B9CC' },
    { id: 'cpp', label: 'C++', icon: '🔩', color: '#00599C' },
    { id: 'rust', label: 'Rust', icon: '🦀', color: '#CE422B' },
    { id: 'java', label: 'Java', icon: '☕', color: '#ED8B00' },
    { id: 'kotlin', label: 'Kotlin', icon: '🎪', color: '#7F52FF' },
    { id: 'swift', label: 'Swift', icon: '🍎', color: '#FA7343' },
    { id: 'scala', label: 'Scala', icon: '⚡', color: '#DC322F' },
    { id: 'csharp', label: 'C#', icon: '#️⃣', color: '#239120' },
    { id: 'haskell', label: 'Haskell', icon: 'λ', color: '#5D4F85' },
  ],
  'Scripting': [
    { id: 'bash', label: 'Bash', icon: '📦', color: '#4EAA25' },
    { id: 'powershell', label: 'PowerShell', icon: '🪟', color: '#5391FE' },
    { id: 'perl', label: 'Perl', icon: '🐪', color: '#39457E' },
    { id: 'elixir', label: 'Elixir', icon: '💧', color: '#6E4A7E' },
    { id: 'erlang', label: 'Erlang', icon: '📡', color: '#A90533' },
  ],
  'Data / Config': [
    { id: 'sql', label: 'SQL', icon: '🗄️', color: '#00A4EF' },
    { id: 'dockerfile', label: 'Dockerfile', icon: '🐳', color: '#2496ED' },
    { id: 'terraform', label: 'Terraform', icon: '🔧', color: '#7B42BC' },
    { id: 'yaml', label: 'YAML', icon: '📋', color: '#CB171E' },
    { id: 'html', label: 'HTML', icon: '🌐', color: '#E34F26' },
    { id: 'css', label: 'CSS', icon: '🎨', color: '#1572B6' },
    { id: 'markdown', label: 'Markdown', icon: '📝', color: '#083FA1' },
    { id: 'matlab', label: 'MATLAB', icon: '🔢', color: '#EF7821' },
  ],
};

const ALL_LANGUAGES = Object.values(LANGUAGE_GROUPS).flat();

const CODE_TEMPLATES = {
  python: "Write a Python class for a REST API client with:\n- Async HTTP requests using httpx\n- Retry logic with exponential backoff\n- Request/response logging\n- Type annotations throughout",
  javascript: "Create a JavaScript debounce utility function with:\n- Configurable delay\n- Leading/trailing execution options\n- Cancel functionality\n- Full TypeScript JSDoc types",
  typescript: "Build a TypeScript generic event emitter class with:\n- Type-safe event registration\n- Async event handlers\n- Event history tracking\n- Unsubscribe support",
  rust: "Write a Rust CLI tool using clap that:\n- Reads a CSV file\n- Filters rows by column value\n- Outputs as JSON or CSV\n- Handles errors gracefully",
  go: "Create a Go HTTP server with:\n- Goroutine worker pool\n- Rate limiting middleware\n- Graceful shutdown\n- Structured JSON logging",
  java: "Write a Java Spring Boot REST controller with:\n- CRUD operations\n- Input validation\n- Exception handling\n- Swagger documentation",
  sql: "Write SQL migrations to create:\n- A users table with indexes\n- A posts table with foreign keys\n- Soft delete support\n- Full-text search indexes",
  dockerfile: "Write a production Dockerfile that:\n- Uses multi-stage build\n- Runs as non-root user\n- Includes health check\n- Minimizes image size",
  bash: "Create a Bash deployment script that:\n- Checks prerequisites\n- Pulls latest code\n- Runs database migrations\n- Restarts services with zero downtime",
  terraform: "Write a Terraform module to deploy:\n- AWS ECS Fargate service\n- ALB with HTTPS\n- Auto-scaling policies\n- CloudWatch alarms",
};

export default function DevPanel({ sessionToken, userId, onClose }) {
  const [activeTab, setActiveTab] = useState('codegen');
  
  // Analytics State
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  
  // Webhooks State
  const [outgoingHooks, setOutgoingHooks] = useState([]);
  const [incomingLogs, setIncomingLogs] = useState([]);
  
  // Form State
  const [newHookName, setNewHookName] = useState('');
  const [newHookUrl, setNewHookUrl] = useState('');
  const [newHookService, setNewHookService] = useState('slack');
  
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Terminal State
  const [terminalInput, setTerminalInput] = useState('');
  const [terminalLogs, setTerminalLogs] = useState([
    { type: 'info', text: 'Welcome to JARVIS Sandbox Terminal Console.' },
    { type: 'info', text: 'Type any shell command to execute inside your sandboxed container environment.' }
  ]);
  const [executing, setExecuting] = useState(false);

  // ── Code Generator State ──────────────────────────────────────────────
  const [selectedLang, setSelectedLang] = useState('python');
  const [codePrompt, setCodePrompt] = useState(CODE_TEMPLATES.python);
  const [generatedCode, setGeneratedCode] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [langSearch, setLangSearch] = useState('');
  const [copySuccess, setCopySuccess] = useState(false);
  const [genError, setGenError] = useState('');
  const [langFilter, setLangFilter] = useState('All');
  const codeOutputRef = useRef(null);

  // Fetch analytics/webhooks data
  const fetchData = async () => {
    if (!sessionToken) return;
    setIsLoading(true);
    setErrorMsg('');
    try {
      const headers = { 'Authorization': `Bearer ${sessionToken}` };
      if (activeTab === 'analytics') {
        const [sumRes, histRes] = await Promise.all([
          fetch('/api/analytics/summary', { headers }),
          fetch('/api/analytics/history', { headers })
        ]);
        if (sumRes.ok) setSummary(await sumRes.json());
        if (histRes.ok) setHistory(await histRes.json());
      } else if (activeTab === 'webhooks') {
        const [outRes, incRes] = await Promise.all([
          fetch('/api/webhooks/outgoing', { headers }),
          fetch('/api/webhooks/incoming/logs', { headers })
        ]);
        if (outRes.ok) setOutgoingHooks(await outRes.json());
        if (incRes.ok) setIncomingLogs(await incRes.json());
      }
    } catch (err) {
      setErrorMsg("Failed to fetch data from backend.");
    } finally {
      setIsLoading(false);
    }
  };

  // Load language model info on mount
  useEffect(() => {
    fetch('/api/code/languages')
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setModelInfo(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === 'analytics' || activeTab === 'webhooks') {
      fetchData();
    }
  }, [activeTab, sessionToken]);

  // Update template when language changes
  const handleLangSelect = (langId) => {
    setSelectedLang(langId);
    setGeneratedCode('');
    setGenError('');
    if (CODE_TEMPLATES[langId]) {
      setCodePrompt(CODE_TEMPLATES[langId]);
    }
  };

  // Generate code via Vibe-Coding model
  const handleGenerateCode = async (e) => {
    e.preventDefault();
    if (!codePrompt.trim() || isGenerating) return;
    setIsGenerating(true);
    setGeneratedCode('');
    setGenError('');

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (sessionToken) headers['Authorization'] = `Bearer ${sessionToken}`;

      // Set a temporary informative state showing the model is initializing/warming up
      setGenError('🤖 Warming up model. Please wait, starting generation...');

      const res = await fetch('/api/code/generate', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt: codePrompt.trim(),
          language: selectedLang,
          max_tokens: 2048
        })
      });

      if (res.ok) {
        const data = await res.json();
        setGeneratedCode(data.code || '');
        // Show provider badge
        const provider = data.provider === 'huggingface' ? '✅ Qwen3-Coder-480B (HuggingFace)' : '⚠️ Groq Fallback (HF token not set)';
        setGenError(''); 
        // scroll to output
        setTimeout(() => codeOutputRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        setModelInfo(prev => ({ ...prev, lastProvider: data.provider, lastModel: data.model }));
      } else {
        const err = await res.json().catch(() => ({}));
        if (res.status === 503 || (err.detail && err.detail.includes('loading'))) {
          setGenError('⚠️ HuggingFace model is currently warming up on cold start. Retrying execution...');
        } else {
          setGenError(err.detail || 'Code generation failed. Please try again.');
        }
      }
    } catch (err) {
      setGenError(`Connection error: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(generatedCode).then(() => {
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    });
  };

  // Webhook handlers
  const handleAddWebhook = async (e) => {
    e.preventDefault();
    if (!newHookName.trim() || !newHookUrl.trim()) return;
    setErrorMsg('');
    try {
      const res = await fetch('/api/webhooks/outgoing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${sessionToken}` },
        body: JSON.stringify({ name: newHookName.trim(), url: newHookUrl.trim(), service: newHookService })
      });
      if (res.ok) { setNewHookName(''); setNewHookUrl(''); setNewHookService('slack'); fetchData(); }
      else { const err = await res.json().catch(() => null); setErrorMsg(err?.detail || "Failed to configure outgoing webhook."); }
    } catch (err) { setErrorMsg(err.message); }
  };

  const handleDeleteWebhook = async (id) => {
    if (!window.confirm("Delete this webhook?")) return;
    try {
      const res = await fetch(`/api/webhooks/outgoing/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${sessionToken}` } });
      if (res.ok) fetchData();
    } catch (err) { setErrorMsg(err.message); }
  };

  // Terminal handler
  const handleTerminalSubmit = async (e) => {
    e.preventDefault();
    if (!terminalInput.trim() || executing) return;
    const cmd = terminalInput.trim();
    setTerminalInput('');
    setTerminalLogs(prev => [...prev, { type: 'input', text: `$ ${cmd}` }]);
    setExecuting(true);
    try {
      const res = await fetch('/api/terminal/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${sessionToken}` },
        body: JSON.stringify({ command: cmd })
      });
      if (res.ok) {
        const data = await res.json();
        const logs = [];
        if (data.stdout) logs.push({ type: 'stdout', text: data.stdout });
        if (data.stderr) logs.push({ type: 'stderr', text: data.stderr });
        if (data.error) logs.push({ type: 'error', text: data.error });
        if (!data.stdout && !data.stderr && !data.error) logs.push({ type: 'info', text: `Command completed with exit code: ${data.exit_code}` });
        setTerminalLogs(prev => [...prev, ...logs]);
      } else {
        const err = await res.json().catch(() => null);
        setTerminalLogs(prev => [...prev, { type: 'error', text: `Error: ${err?.detail || 'Failed to run command'}` }]);
      }
    } catch (err) {
      setTerminalLogs(prev => [...prev, { type: 'error', text: `Connection error: ${err.message}` }]);
    } finally {
      setExecuting(false);
    }
  };

  const getIncomingUrl = (source) => `${window.location.origin}/api/webhooks/incoming/${userId}/${source}`;

  // Filter languages for sidebar
  const filteredGroups = {};
  Object.entries(LANGUAGE_GROUPS).forEach(([group, langs]) => {
    if (langFilter !== 'All' && langFilter !== group) return;
    const filtered = langs.filter(l =>
      l.label.toLowerCase().includes(langSearch.toLowerCase()) ||
      l.id.toLowerCase().includes(langSearch.toLowerCase())
    );
    if (filtered.length > 0) filteredGroups[group] = filtered;
  });

  const selectedLangObj = ALL_LANGUAGES.find(l => l.id === selectedLang);

  return (
    <div className="dev-panel-overlay">
      <style>{`
        .dev-panel-overlay {
          position: fixed; inset: 0; z-index: 900;
          background: rgba(4, 4, 12, 0.75);
          backdrop-filter: blur(18px);
          display: flex; align-items: center; justify-content: center;
          color: #e8eaff;
          font-family: 'Inter', system-ui, sans-serif;
        }
        .dev-card {
          width: 1080px; max-width: 96vw;
          height: 720px; max-height: 92vh;
          background: rgba(8, 8, 28, 0.88);
          border: 1px solid rgba(100, 120, 255, 0.18);
          border-radius: 22px;
          box-shadow: 0 24px 60px rgba(0,0,0,0.7), 0 0 40px rgba(0, 212, 255, 0.06);
          display: flex; flex-direction: column; overflow: hidden; position: relative;
        }
        .dev-header {
          padding: 20px 28px;
          border-bottom: 1px solid rgba(255,255,255,0.07);
          display: flex; justify-content: space-between; align-items: center;
          background: rgba(0,0,0,0.2);
        }
        .dev-title-area { display: flex; align-items: center; gap: 12px; }
        .dev-icon { font-size: 1.5rem; }
        .dev-title {
          font-size: 1.15rem; font-weight: 800; letter-spacing: 1.5px;
          background: linear-gradient(135deg, #00d4ff, #7c3aed);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .dev-subtitle {
          font-size: 0.72rem; color: #6b7aad; letter-spacing: 0.5px; margin-top: 2px;
        }
        .model-badge {
          display: flex; align-items: center; gap: 6px;
          background: rgba(0, 212, 255, 0.08);
          border: 1px solid rgba(0, 212, 255, 0.2);
          border-radius: 20px; padding: 4px 12px;
          font-size: 0.7rem; color: #00d4ff; font-weight: 600;
        }
        .dev-close-btn {
          background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
          color: #8b8fad; font-size: 1.2rem; cursor: pointer;
          border-radius: 8px; width: 32px; height: 32px;
          display: flex; align-items: center; justify-content: center;
          transition: all 0.2s;
        }
        .dev-close-btn:hover { color: #ff4a6b; border-color: rgba(255,74,107,0.3); background: rgba(255,74,107,0.1); }
        .dev-nav {
          display: flex; padding: 0 24px;
          border-bottom: 1px solid rgba(255,255,255,0.05);
          gap: 6px; background: rgba(0,0,0,0.12);
        }
        .nav-tab {
          padding: 14px 16px; font-size: 0.78rem; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.8px; color: #6b7aad;
          background: none; border: none; border-bottom: 2px solid transparent;
          cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 6px;
        }
        .nav-tab.active { color: #00d4ff; border-bottom-color: #00d4ff; }
        .nav-tab:hover:not(.active) { color: #a0aec0; }
        .dev-body {
          flex: 1; overflow-y: auto; display: flex; flex-direction: column;
        }

        /* ── Code Generator Layout ── */
        .codegen-layout {
          display: grid; grid-template-columns: 220px 1fr;
          flex: 1; overflow: hidden;
        }
        .lang-sidebar {
          border-right: 1px solid rgba(255,255,255,0.05);
          overflow-y: auto; padding: 12px 8px;
          background: rgba(0,0,0,0.15);
          display: flex; flex-direction: column; gap: 2px;
        }
        .lang-search-wrap { padding: 0 4px 8px; }
        .lang-search {
          width: 100%; padding: 6px 10px; background: rgba(0,0,0,0.3);
          border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
          color: white; font-size: 0.75rem; outline: none;
          transition: border-color 0.2s;
        }
        .lang-search:focus { border-color: #00d4ff; }
        .lang-group-label {
          font-size: 0.6rem; text-transform: uppercase; letter-spacing: 1.2px;
          color: #4a5270; padding: 8px 8px 4px; font-weight: 700;
        }
        .lang-btn {
          width: 100%; display: flex; align-items: center; gap: 8px;
          padding: 7px 10px; border: none; border-radius: 8px;
          background: transparent; color: #8b8fad; cursor: pointer;
          font-size: 0.78rem; font-weight: 500; text-align: left;
          transition: all 0.15s; position: relative;
        }
        .lang-btn:hover { background: rgba(255,255,255,0.04); color: #c0c6e0; }
        .lang-btn.active { background: rgba(0, 212, 255, 0.1); color: #00d4ff; font-weight: 700; }
        .lang-btn.active::before {
          content: ''; position: absolute; left: 0; top: 2px; bottom: 2px;
          width: 3px; background: #00d4ff; border-radius: 0 2px 2px 0;
        }
        .lang-icon { font-size: 1rem; width: 18px; text-align: center; flex-shrink: 0; }

        /* ── Code Generator Main ── */
        .codegen-main {
          display: flex; flex-direction: column; overflow: hidden; flex: 1;
        }
        .codegen-header {
          padding: 16px 20px 12px;
          border-bottom: 1px solid rgba(255,255,255,0.05);
          display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
        }
        .lang-selected-badge {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 4px 12px; border-radius: 20px;
          font-size: 0.8rem; font-weight: 700; letter-spacing: 0.5px;
        }
        .model-provider-badge {
          font-size: 0.68rem; padding: 3px 8px;
          border-radius: 4px; font-weight: 600;
          background: rgba(0, 212, 255, 0.1);
          border: 1px solid rgba(0, 212, 255, 0.2);
          color: #00d4ff;
        }
        .model-provider-badge.fallback {
          background: rgba(251, 191, 36, 0.1);
          border-color: rgba(251, 191, 36, 0.2);
          color: #fbbf24;
        }
        .codegen-body { 
          flex: 1; overflow-y: auto; padding: 16px 20px;
          display: flex; flex-direction: column; gap: 14px;
        }
        .prompt-section label {
          display: block; font-size: 0.72rem; text-transform: uppercase;
          letter-spacing: 1px; color: #6b7aad; margin-bottom: 8px; font-weight: 700;
        }
        .prompt-textarea {
          width: 100%; padding: 12px 14px; min-height: 100px; max-height: 180px;
          background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08);
          border-radius: 12px; color: #e8eaff; font-size: 0.84rem;
          font-family: inherit; resize: vertical; outline: none;
          transition: border-color 0.2s; line-height: 1.5; box-sizing: border-box;
        }
        .prompt-textarea:focus { border-color: rgba(0, 212, 255, 0.4); }
        .generate-btn {
          padding: 10px 24px; font-size: 0.85rem; font-weight: 700;
          background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 100%);
          border: none; border-radius: 10px; color: white; cursor: pointer;
          transition: all 0.2s; display: flex; align-items: center; gap: 8px;
          letter-spacing: 0.5px; box-shadow: 0 4px 15px rgba(0,212,255,0.25);
        }
        .generate-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,212,255,0.35); }
        .generate-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .gen-spinner {
          width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3);
          border-top-color: white; border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .code-output-section {
          background: rgba(0,0,0,0.35);
          border: 1px solid rgba(255,255,255,0.06);
          border-radius: 14px; overflow: hidden;
        }
        .code-output-header {
          display: flex; justify-content: space-between; align-items: center;
          padding: 10px 14px; background: rgba(0,0,0,0.3);
          border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .code-output-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #6b7aad; font-weight: 700; }
        .copy-btn {
          padding: 4px 12px; background: rgba(124,58,237,0.15);
          border: 1px solid rgba(124,58,237,0.3); color: #a78bfa;
          border-radius: 6px; font-size: 0.7rem; cursor: pointer; font-weight: 600;
          transition: all 0.2s;
        }
        .copy-btn:hover { background: rgba(124,58,237,0.25); }
        .copy-btn.success { background: rgba(52,211,153,0.15); border-color: rgba(52,211,153,0.3); color: #34d399; }
        .code-block {
          padding: 14px 16px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 0.8rem; color: #a8d8ea; line-height: 1.6;
          white-space: pre-wrap; word-break: break-word; max-height: 300px;
          overflow-y: auto;
        }
        .gen-error {
          padding: 10px 14px; background: rgba(244,63,94,0.08);
          border: 1px solid rgba(244,63,94,0.2); border-radius: 10px;
          color: #f43f5e; font-size: 0.8rem;
        }
        .gen-placeholder {
          padding: 32px; text-align: center; color: #4a5270; font-size: 0.85rem;
        }
        .gen-placeholder .placeholder-icon { font-size: 2.5rem; margin-bottom: 10px; }
        .generate-row { display: flex; gap: 10px; align-items: flex-start; flex-wrap: wrap; }
        .template-btn {
          padding: 5px 10px; font-size: 0.7rem; background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08); border-radius: 6px;
          color: #8b8fad; cursor: pointer; transition: all 0.15s;
        }
        .template-btn:hover { background: rgba(0,212,255,0.08); border-color: rgba(0,212,255,0.2); color: #00d4ff; }

        /* ── Reuse existing styles from before ── */
        .dev-body-padded { flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 24px; }
        .dev-error { padding: 12px; background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.2); border-radius: 8px; color: #f43f5e; font-size: 0.8rem; }
        .analytics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .metric-card { padding: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; text-align: center; }
        .metric-label { font-size: 0.7rem; color: #8b8fad; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .metric-value { font-size: 1.4rem; font-weight: 700; color: #00d4ff; }
        .section-title { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1.5px; color: #a78bfa; margin-bottom: 12px; font-weight: 700; border-left: 2px solid #a78bfa; padding-left: 8px; }
        .webhook-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 16px; }
        .webhook-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .webhook-row:last-child { border-bottom: none; }
        .webhook-info { display: flex; flex-direction: column; gap: 4px; }
        .webhook-name { font-weight: 600; font-size: 0.9rem; }
        .webhook-url { font-size: 0.75rem; color: #8b8fad; font-family: monospace; }
        .webhook-service-badge { display: inline-block; padding: 2px 6px; font-size: 0.6rem; background: rgba(124,58,237,0.2); border: 1px solid rgba(124,58,237,0.3); color: #a78bfa; border-radius: 4px; text-transform: uppercase; font-weight: bold; align-self: flex-start; }
        .webhook-del-btn { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.2); color: #f43f5e; padding: 6px 12px; border-radius: 6px; font-size: 0.75rem; cursor: pointer; transition: all 0.2s; }
        .webhook-del-btn:hover { background: rgba(244,63,94,0.25); border-color: #f43f5e; }
        .webhook-form { display: grid; grid-template-columns: 1fr 2fr 1fr auto; gap: 12px; align-items: end; }
        .form-label { display: block; font-size: 0.7rem; color: #8b8fad; text-transform: uppercase; margin-bottom: 6px; }
        .form-input, .form-select { width: 100%; padding: 8px 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; color: white; font-size: 0.8rem; outline: none; }
        .form-input:focus, .form-select:focus { border-color: #00d4ff; }
        .add-btn { padding: 8px 16px; background: rgba(0,212,255,0.15); border: 1px solid rgba(0,212,255,0.3); color: #00d4ff; border-radius: 8px; font-weight: 700; font-size: 0.8rem; cursor: pointer; height: 34px; }
        .add-btn:hover { background: rgba(0,212,255,0.3); border-color: #00d4ff; }
        .analytics-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
        .analytics-table th, .analytics-table td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .analytics-table th { color: #8b8fad; font-weight: 600; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px; }
        .copy-url-btn { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #a78bfa; padding: 4px 8px; border-radius: 4px; font-size: 0.65rem; cursor: pointer; margin-left: 8px; }
        .copy-url-btn:hover { background: rgba(124,58,237,0.2); border-color: #a78bfa; }

        /* Terminal */
        .terminal-body {
          flex: 1; padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;
        }
      `}</style>

      <div className="dev-card">
        {/* Header */}
        <div className="dev-header">
          <div className="dev-title-area">
            <span className="dev-icon">💻</span>
            <div>
              <h3 className="dev-title">Developer Suite & Code Generator</h3>
              <div className="dev-subtitle">30+ Languages · Qwen3-Coder-480B-A35B-Instruct · FLUX.1-dev · Whisper-v3 · Kokoro-82M</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {modelInfo && (
              <a
                href={`https://huggingface.co/Qwen/Qwen3-Coder-480B-A35B-Instruct`}
                target="_blank"
                rel="noopener noreferrer"
                className="model-badge"
                style={{ textDecoration: 'none' }}
              >
                🤗 Qwen3-Coder-480B
                &nbsp;<span style={{ opacity: 0.6 }}>{modelInfo.total} langs</span>
              </a>
            )}
            <button className="dev-close-btn" onClick={onClose}>✕</button>
          </div>
        </div>

        {/* Navigation */}
        <div className="dev-nav">
          <button className={`nav-tab ${activeTab === 'codegen' ? 'active' : ''}`} onClick={() => setActiveTab('codegen')}>
            🤖 Code Generator
          </button>
          <button className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            📊 Analytics
          </button>
          <button className={`nav-tab ${activeTab === 'webhooks' ? 'active' : ''}`} onClick={() => setActiveTab('webhooks')}>
            🔗 Webhooks
          </button>
          <button className={`nav-tab ${activeTab === 'terminal' ? 'active' : ''}`} onClick={() => setActiveTab('terminal')}>
            💻 Terminal
          </button>
        </div>

        {/* Body */}
        <div className="dev-body">

          {/* ── Code Generator Tab ── */}
          {activeTab === 'codegen' && (
            <div className="codegen-layout">
              {/* Language Sidebar */}
              <div className="lang-sidebar">
                <div className="lang-search-wrap">
                  <input
                    type="text"
                    className="lang-search"
                    placeholder="🔍 Search language..."
                    value={langSearch}
                    onChange={e => setLangSearch(e.target.value)}
                  />
                </div>
                {Object.entries(filteredGroups).map(([group, langs]) => (
                  <div key={group}>
                    <div className="lang-group-label">{group}</div>
                    {langs.map(lang => (
                      <button
                        key={lang.id}
                        className={`lang-btn ${selectedLang === lang.id ? 'active' : ''}`}
                        onClick={() => handleLangSelect(lang.id)}
                      >
                        <span className="lang-icon">{lang.icon}</span>
                        <span>{lang.label}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>

              {/* Generator Main Area */}
              <div className="codegen-main">
                <div className="codegen-header">
                  <span
                    className="lang-selected-badge"
                    style={{
                      background: `${selectedLangObj?.color || '#00d4ff'}18`,
                      border: `1px solid ${selectedLangObj?.color || '#00d4ff'}40`,
                      color: selectedLangObj?.color || '#00d4ff',
                    }}
                  >
                    {selectedLangObj?.icon} {selectedLangObj?.label || selectedLang.toUpperCase()}
                  </span>
                  {modelInfo?.lastProvider && (
                    <span className={`model-provider-badge ${modelInfo.lastProvider === 'groq_fallback' ? 'fallback' : ''}`}>
                      {modelInfo.lastProvider === 'huggingface'
                        ? '✅ Vibe-Coding-Claude-Fable-5'
                        : '⚠️ Groq Fallback (Set HUGGINGFACE_API_TOKEN)'}
                    </span>
                  )}
                  {!modelInfo?.lastProvider && (
                    <span style={{ fontSize: '0.68rem', color: '#4a5270' }}>
                      → Qwen3-Coder-480B-A35B-Instruct via HuggingFace /v1
                    </span>
                  )}
                </div>

                <div className="codegen-body">
                  {/* Prompt Input */}
                  <form onSubmit={handleGenerateCode} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div className="prompt-section">
                      <label>Describe what you want to build</label>
                      <textarea
                        className="prompt-textarea"
                        value={codePrompt}
                        onChange={e => setCodePrompt(e.target.value)}
                        placeholder={`Describe the ${selectedLangObj?.label || selectedLang} code you need...`}
                        disabled={isGenerating}
                      />
                    </div>
                    
                    {/* Quick templates */}
                    {CODE_TEMPLATES[selectedLang] && (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.65rem', color: '#4a5270', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Templates:</span>
                        <button type="button" className="template-btn" onClick={() => setCodePrompt(CODE_TEMPLATES[selectedLang])}>
                          📋 Load Example
                        </button>
                        <button type="button" className="template-btn" onClick={() => setCodePrompt('')}>
                          🗑️ Clear
                        </button>
                      </div>
                    )}

                    <div className="generate-row">
                      <button type="submit" className="generate-btn" disabled={isGenerating || !codePrompt.trim()}>
                        {isGenerating ? (
                          <><div className="gen-spinner" /> Generating...</>
                        ) : (
                          <>🤖 Generate {selectedLangObj?.label} Code</>
                        )}
                      </button>
                      {isGenerating && (
                        <span style={{ fontSize: '0.72rem', color: '#6b7aad', alignSelf: 'center' }}>
                          Calling Qwen3-Coder-480B (HuggingFace /v1)...
                        </span>
                      )}
                    </div>
                  </form>

                  {/* Error */}
                  {genError && <div className="gen-error">⚠️ {genError}</div>}

                  {/* Output */}
                  {generatedCode ? (
                    <div className="code-output-section" ref={codeOutputRef}>
                      <div className="code-output-header">
                        <span className="code-output-title">
                          {selectedLangObj?.icon} {selectedLangObj?.label} Output
                          {modelInfo?.lastModel && (
                            <span style={{ marginLeft: 8, color: '#4a5270', fontWeight: 400 }}>
                              · {modelInfo.lastModel.split('/').pop()}
                            </span>
                          )}
                        </span>
                        <button
                          className={`copy-btn ${copySuccess ? 'success' : ''}`}
                          onClick={handleCopyCode}
                        >
                          {copySuccess ? '✅ Copied!' : '📋 Copy Code'}
                        </button>
                      </div>
                      <div className="code-block">{generatedCode}</div>
                    </div>
                  ) : !isGenerating && (
                    <div className="gen-placeholder">
                      <div className="placeholder-icon">{selectedLangObj?.icon || '💻'}</div>
                      <div>Describe your {selectedLangObj?.label || selectedLang} requirements above</div>
                      <div style={{ fontSize: '0.7rem', color: '#363d5a', marginTop: 6 }}>
                        Powered by <strong style={{ color: '#00d4ff' }}>Qwen3-Coder-480B-A35B-Instruct</strong> — HuggingFace
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Analytics Tab ── */}
          {activeTab === 'analytics' && (
            <div className="dev-body-padded">
              {errorMsg && <div className="dev-error">{errorMsg}</div>}
              {isLoading && <div style={{ color: '#00d4ff', fontSize: '0.9rem' }}>Loading analytics...</div>}
              <div className="analytics-grid">
                <div className="metric-card">
                  <div className="metric-label">Total Queries</div>
                  <div className="metric-value">{summary?.total_queries || 0}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Prompt Tokens</div>
                  <div className="metric-value" style={{ color: '#a78bfa' }}>{summary?.total_prompt_tokens?.toLocaleString() || 0}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Completion Tokens</div>
                  <div className="metric-value" style={{ color: '#f472b6' }}>{summary?.total_completion_tokens?.toLocaleString() || 0}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Accumulated Cost</div>
                  <div className="metric-value" style={{ color: '#34d399' }}>${summary?.total_cost_usd?.toFixed(6) || '0.000000'}</div>
                </div>
              </div>

              <div>
                <h4 className="section-title">Query Step Performance</h4>
                <div className="webhook-card">
                  <table className="analytics-table">
                    <thead><tr><th>Step</th><th>Tokens</th><th>Cost</th><th>Avg Latency</th></tr></thead>
                    <tbody>
                      {summary?.breakdown_by_step?.map((step, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 'bold' }}>{step.step_name}</td>
                          <td>{step.total_tokens.toLocaleString()}</td>
                          <td style={{ color: '#34d399' }}>${step.estimated_cost_usd.toFixed(6)}</td>
                          <td>{step.avg_latency_ms.toFixed(1)}ms</td>
                        </tr>
                      )) || <tr><td colSpan="4" style={{ textAlign: 'center', color: '#8b8fad' }}>No records yet.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="section-title">Recent LLM Executions</h4>
                <div className="webhook-card" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  <table className="analytics-table">
                    <thead><tr><th>Step</th><th>Model</th><th>Tokens</th><th>Cost</th><th>Latency</th><th>Time</th></tr></thead>
                    <tbody>
                      {history.slice(0, 15).map((log) => (
                        <tr key={log.id}>
                          <td>{log.step_name}</td>
                          <td style={{ color: '#8b8fad', fontFamily: 'monospace', fontSize: '0.75rem' }}>{log.model_name}</td>
                          <td>{log.total_tokens}</td>
                          <td style={{ color: '#34d399' }}>${log.estimated_cost_usd.toFixed(6)}</td>
                          <td>{log.latency_ms.toFixed(0)}ms</td>
                          <td style={{ color: '#8b8fad', fontSize: '0.75rem' }}>{new Date(log.timestamp).toLocaleTimeString()}</td>
                        </tr>
                      )) || <tr><td colSpan="6" style={{ textAlign: 'center', color: '#8b8fad' }}>No history yet.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ── Webhooks Tab ── */}
          {activeTab === 'webhooks' && (
            <div className="dev-body-padded">
              {errorMsg && <div className="dev-error">{errorMsg}</div>}
              <div>
                <h4 className="section-title">Configure Outgoing Webhooks</h4>
                <div className="webhook-card" style={{ marginBottom: 16 }}>
                  <form onSubmit={handleAddWebhook} className="webhook-form">
                    <div><label className="form-label">Name</label><input type="text" className="form-input" placeholder="Slack General" value={newHookName} onChange={e => setNewHookName(e.target.value)} required /></div>
                    <div><label className="form-label">Webhook URL</label><input type="url" className="form-input" placeholder="https://hooks.slack.com/..." value={newHookUrl} onChange={e => setNewHookUrl(e.target.value)} required /></div>
                    <div><label className="form-label">Service</label>
                      <select className="form-select" value={newHookService} onChange={e => setNewHookService(e.target.value)}>
                        <option value="slack">Slack</option><option value="discord">Discord</option><option value="generic">Generic JSON</option>
                      </select>
                    </div>
                    <button type="submit" className="add-btn">Add Hook</button>
                  </form>
                </div>
                <div className="webhook-card">
                  {outgoingHooks.length > 0 ? outgoingHooks.map(hook => (
                    <div key={hook.id} className="webhook-row">
                      <div className="webhook-info">
                        <span className="webhook-name">{hook.name}</span>
                        <span className="webhook-url">{hook.url}</span>
                        <span className="webhook-service-badge">{hook.service}</span>
                      </div>
                      <button className="webhook-del-btn" onClick={() => handleDeleteWebhook(hook.id)}>Delete</button>
                    </div>
                  )) : <div style={{ textAlign: 'center', color: '#8b8fad', fontSize: '0.8rem' }}>No webhooks configured.</div>}
                </div>
              </div>

              <div>
                <h4 className="section-title">Incoming Trigger URLs</h4>
                <div className="webhook-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {['github', 'stripe'].map(src => (
                    <div key={src}>
                      <label className="form-label" style={{ marginBottom: 4 }}>{src.charAt(0).toUpperCase() + src.slice(1)} Hook URL</label>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <input type="text" className="form-input" readOnly value={getIncomingUrl(src)} style={{ fontFamily: 'monospace', flex: 1 }} />
                        <button className="copy-url-btn" onClick={() => { navigator.clipboard.writeText(getIncomingUrl(src)); }}>Copy</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Terminal Tab ── */}
          {activeTab === 'terminal' && (
            <div className="terminal-body">
              <h4 className="section-title">Isolated Container Sandbox Shell</h4>
              <div style={{
                flex: 1, backgroundColor: '#05070f', border: '1px solid #1e293b',
                borderRadius: 12, padding: 16, fontFamily: 'Consolas, Monaco, monospace',
                fontSize: '0.85rem', color: '#4ade80', overflowY: 'auto',
                display: 'flex', flexDirection: 'column', gap: 8,
                maxHeight: 400, minHeight: 250
              }}>
                {terminalLogs.map((log, idx) => (
                  <div key={idx} style={{
                    whiteSpace: 'pre-wrap',
                    color: log.type === 'input' ? '#38bdf8' : log.type === 'stderr' || log.type === 'error' ? '#ef4444' : log.type === 'info' ? '#94a3b8' : '#4ade80'
                  }}>{log.text}</div>
                ))}
                {executing && <div style={{ color: '#e2e8f0' }}>Running command...</div>}
              </div>
              <form onSubmit={handleTerminalSubmit} style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <input
                  type="text" className="form-input"
                  placeholder="Type shell command (e.g. python --version, ls -la)..."
                  value={terminalInput} onChange={e => setTerminalInput(e.target.value)}
                  disabled={executing} style={{ fontFamily: 'monospace' }}
                />
                <button type="submit" className="add-btn" disabled={executing} style={{ height: 38, minWidth: 80 }}>
                  {executing ? '...' : 'Run'}
                </button>
                <button type="button" className="webhook-del-btn" onClick={() => setTerminalLogs([{ type: 'info', text: 'Console cleared.' }])} style={{ height: 38 }}>
                  Clear
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
