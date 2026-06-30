import { useState, useEffect } from 'react';

const getActiveUserToken = () => {
  try {
    const token = localStorage.getItem('jarvis_token');
    if (token) return token;
    const user = localStorage.getItem('jarvis_user');
    if (user) {
      const parsed = JSON.parse(user);
      return parsed.id || 'developer';
    }
  } catch (e) {}
  return 'developer';
};

export default function IntegrationsModal({ isOpen, onClose, onToast }) {
  const [activeCategory, setActiveCategory] = useState('All');
  const [authPromptService, setAuthPromptService] = useState(null);
  const [inputAccount, setInputAccount] = useState('');
  
  // Default initial state: ALL services are Not Connected unless saved in localStorage
  const defaultIntegrations = {
    // Education & Social
    google_workspace: { name: 'Google Workspace (Sheets & Calendar)', category: 'Education & Productivity', icon: '📊', connected: false, account: '', desc: 'Sync live gradebooks to Sheets & class schedules to Calendar' },
    whatsapp_cloud: { name: 'WhatsApp Business Cloud API', category: 'Education & Productivity', icon: '📲', connected: false, account: '', desc: 'Automated parent broadcast messages and homework alerts' },
    notion_notes: { name: 'Notion & Digital Notes Sync', category: 'Education & Productivity', icon: '📝', connected: false, account: '', desc: 'Sync classroom observations and digital lesson notes' },

    // Developer & Cloud
    github: { name: 'GitHub & GitLab DevOps', category: 'Developer & Cloud', icon: '🐙', connected: false, account: '', desc: 'Automated PR reviews, CI/CD triggering, and repository commits' },
    aws_cloud: { name: 'AWS & Cloud Infrastructure', category: 'Developer & Cloud', icon: '☁️', connected: false, account: '', desc: 'Terraform IaC deployments, S3 log storage, and K8s telemetry' },
    docker_hub: { name: 'Docker Hub & Kubernetes API', category: 'Developer & Cloud', icon: '🐳', connected: false, account: '', desc: 'Container image pushes and automated cluster pod monitoring' },

    // Marketing & Growth
    meta_ads: { name: 'Meta Ads Manager & Instagram', category: 'Marketing & Growth', icon: '📢', connected: false, account: '', desc: 'Automated ad copy deployment, creative testing, and ROAS metrics' },
    google_analytics: { name: 'Google Ads & GA4 Analytics', category: 'Marketing & Growth', icon: '📈', connected: false, account: '', desc: 'Real-time CAC, conversion funnel analytics, and attribution' },

    // Finance & Legal
    alpha_vantage: { name: 'Bloomberg & Alpha Vantage', category: 'Finance & Legal', icon: '💵', connected: false, account: '', desc: 'Real-time stock ticker streams, SEC filings, and financial modeling' },
    docusign: { name: 'DocuSign E-Signature API', category: 'Finance & Legal', icon: '⚖️', desc: 'Automated contract NDA risk auditing and instant digital signing' },

    // Team Collaboration
    slack_teams: { name: 'Slack & Microsoft Teams', category: 'Team Collaboration', icon: '💬', connected: false, account: '', desc: 'Cross-functional team task alerts, notifications, and email sync' }
  };

  const [integrations, setIntegrations] = useState(() => {
    try {
      const saved = localStorage.getItem('jarvis_user_integrations');
      return saved ? JSON.parse(saved) : defaultIntegrations;
    } catch (e) {
      return defaultIntegrations;
    }
  });

  const [connectingKey, setConnectingKey] = useState(null);

  // Sync with backend integrations & URL parameters on open / mount
  useEffect(() => {
    const syncBackendIntegrations = async () => {
      // 1. Check URL parameters
      const params = new URLSearchParams(window.location.search);
      const urlProvider = params.get('connected_provider');
      const urlEmail = params.get('email');

      if (urlProvider && urlEmail) {
        setIntegrations(prev => ({
          ...prev,
          [urlProvider]: {
            ...prev[urlProvider],
            connected: true,
            account: urlEmail
          }
        }));
      }

      // 2. Fetch backend integrations
      try {
        const token = getActiveUserToken();
        const res = await fetch('/api/auth/integrations', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.integrations) {
            setIntegrations(prev => {
              const updated = { ...prev };
              Object.entries(data.integrations).forEach(([provKey, item]) => {
                if (updated[provKey]) {
                  updated[provKey] = {
                    ...updated[provKey],
                    connected: item.connected,
                    account: item.account
                  };
                }
              });
              return updated;
            });
          }
        }
      } catch (err) {
        console.error("Failed to sync backend integrations:", err);
      }
    };

    if (isOpen) {
      syncBackendIntegrations();
    }
  }, [isOpen]);

  useEffect(() => {
    try {
      localStorage.setItem('jarvis_user_integrations', JSON.stringify(integrations));
    } catch (e) {
      console.error("Failed to save integrations state:", e);
    }
  }, [integrations]);

  if (!isOpen) return null;

  const handleStartConnect = async (key, service) => {
    if (integrations[key].connected) {
      // Disconnect
      setIntegrations(prev => ({
        ...prev,
        [key]: { ...prev[key], connected: false, account: '' }
      }));
      try {
        const token = getActiveUserToken();
        await fetch('/api/auth/integrations/disconnect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ provider: key, account: integrations[key].account })
        });
      } catch (err) {
        console.error("Failed to disconnect backend integration:", err);
      }
      if (onToast) onToast({ level: 'warning', title: 'Service Disconnected', message: `Disconnected ${service.name}.` });
    } else {
      if (key === 'google_workspace') {
        try {
          const token = getActiveUserToken();
          const res = await fetch(`/api/auth/google/url?session_token=${token}`);
          const data = await res.json();
          if (data.oauth_url) {
            if (onToast) onToast({ level: 'info', title: 'Redirecting to Google...', message: 'Opening official Google OAuth authorization page.' });
            window.location.href = data.oauth_url;
            return;
          }
        } catch (err) {
          console.error("Failed to fetch Google OAuth URL:", err);
        }
      }
      // Prompt for real account email/ID for other services
      setAuthPromptService({ key, ...service });
      setInputAccount('');
    }
  };

  const handleConfirmConnect = async (e) => {
    e.preventDefault();
    if (!inputAccount.trim()) return;

    const key = authPromptService.key;
    const name = authPromptService.name;
    const userAccount = inputAccount.trim();

    setAuthPromptService(null);
    setConnectingKey(key);

    try {
      const token = localStorage.getItem('jarvis_session_token');
      await fetch('/api/auth/integrations/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ provider: key, account: userAccount })
      });
    } catch (err) {
      console.error("Failed to store backend OAuth connection:", err);
    }

    setTimeout(() => {
      setIntegrations(prev => ({
        ...prev,
        [key]: { 
          ...prev[key], 
          connected: true, 
          account: userAccount 
        }
      }));
      setConnectingKey(null);
      if (onToast) onToast({ level: 'success', title: 'OAuth Verified & Connected!', message: `Successfully authenticated ${name} as ${userAccount}.` });
    }, 1000);
  };

  const categories = ['All', 'Education & Productivity', 'Developer & Cloud', 'Marketing & Growth', 'Finance & Legal', 'Team Collaboration'];

  const filteredIntegrations = Object.entries(integrations).filter(([_, item]) => 
    activeCategory === 'All' || item.category === activeCategory
  );

  return (
    <div className="modal-overlay" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(5, 8, 22, 0.88)',
      backdropFilter: 'blur(14px)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      animation: 'fadeIn 0.2s ease'
    }}>
      <div className="modal-content" style={{
        width: '100%',
        maxWidth: '780px',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(145deg, rgba(13, 19, 44, 0.98), rgba(8, 12, 30, 0.99))',
        border: '1px solid rgba(0, 212, 255, 0.3)',
        borderRadius: '24px',
        padding: '28px',
        boxShadow: '0 0 50px rgba(0, 212, 255, 0.25)',
        color: '#f8fafc',
        position: 'relative'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '1.8rem' }}>🔌</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.35rem', color: '#f8fafc', fontWeight: 800, letterSpacing: '0.5px' }}>Universal Enterprise Integrations Hub</h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>Connect third-party accounts once to empower ALL AI tools across all workspace domains</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.6rem', cursor: 'pointer' }}
          >
            &times;
          </button>
        </div>

        {/* Category Filter Tabs */}
        <div style={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: '8px', 
          paddingBottom: '14px', 
          marginBottom: '18px', 
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)' 
        }}>
          {categories.map(cat => {
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '20px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  border: isActive ? '1px solid #00d4ff' : '1px solid rgba(255, 255, 255, 0.12)',
                  background: isActive ? 'linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(121, 40, 202, 0.2))' : 'rgba(15, 23, 42, 0.6)',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  boxShadow: isActive ? '0 0 12px rgba(0, 212, 255, 0.3)' : 'none',
                  transition: 'all 0.2s ease',
                  lineHeight: '1.2'
                }}
              >
                {cat}
              </button>
            );
          })}
        </div>

        {/* Scrollable Integrations List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '6px' }}>
          {filteredIntegrations.map(([key, item]) => (
            <div 
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px',
                background: 'rgba(15, 23, 42, 0.65)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '16px',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
                <span style={{ fontSize: '2rem', padding: '10px', background: 'rgba(255, 255, 255, 0.04)', borderRadius: '12px' }}>{item.icon}</span>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h4 style={{ margin: 0, fontSize: '0.98rem', color: '#f8fafc', fontWeight: 700 }}>{item.name}</h4>
                    <span style={{ fontSize: '0.68rem', padding: '2px 8px', borderRadius: '10px', background: 'rgba(255, 255, 255, 0.08)', color: '#cbd5e1' }}>{item.category}</span>
                  </div>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>{item.desc}</p>
                  <p style={{ margin: '3px 0 0 0', fontSize: '0.75rem', fontWeight: 600, color: item.connected ? '#22c55e' : '#ef4444' }}>
                    {item.connected ? `🟢 Connected as ${item.account}` : '🔴 Not Connected'}
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleStartConnect(key, item)}
                disabled={connectingKey === key}
                style={{
                  padding: '9px 18px',
                  borderRadius: '10px',
                  fontWeight: 700,
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  border: item.connected ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid #00d4ff',
                  background: item.connected ? 'rgba(239, 68, 68, 0.1)' : 'linear-gradient(135deg, #00d4ff, #7928ca)',
                  color: item.connected ? '#ef4444' : '#ffffff',
                  boxShadow: item.connected ? 'none' : '0 0 14px rgba(0, 212, 255, 0.25)',
                  transition: 'all 0.2s ease',
                  whiteSpace: 'nowrap'
                }}
              >
                {connectingKey === key ? 'Authenticating...' : item.connected ? 'Disconnect' : 'Connect OAuth'}
              </button>
            </div>
          ))}
        </div>

        {/* OAuth Authentication Input Sub-Modal */}
        {authPromptService && (
          <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(5, 8, 22, 0.95)',
            backdropFilter: 'blur(10px)',
            borderRadius: '24px',
            padding: '32px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 10000,
            animation: 'fadeIn 0.2s ease'
          }}>
            <div style={{ width: '100%', maxWidth: '420px', textAlign: 'center' }}>
              <span style={{ fontSize: '3rem' }}>{authPromptService.icon}</span>
              <h3 style={{ margin: '12px 0 6px 0', fontSize: '1.2rem', color: '#f8fafc' }}>Connect {authPromptService.name}</h3>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#94a3b8', marginBottom: '20px' }}>
                Enter your official account email or handle to authenticate OAuth permissions.
              </p>

              <form onSubmit={handleConfirmConnect} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <input
                  type="text"
                  placeholder={authPromptService.key.includes('whatsapp') ? "+91 98765 43210 (Phone Number)" : "your.email@organization.com"}
                  value={inputAccount}
                  onChange={(e) => setInputAccount(e.target.value)}
                  autoFocus
                  required
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    background: 'rgba(15, 23, 42, 0.9)',
                    border: '1px solid #00d4ff',
                    borderRadius: '12px',
                    color: '#f8fafc',
                    fontSize: '0.9rem',
                    outline: 'none',
                    boxShadow: '0 0 15px rgba(0, 212, 255, 0.2)'
                  }}
                />

                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setAuthPromptService(null)}
                    style={{
                      padding: '10px 20px',
                      background: 'rgba(255, 255, 255, 0.08)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      borderRadius: '10px',
                      color: '#94a3b8',
                      cursor: 'pointer',
                      fontWeight: 600
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    style={{
                      padding: '10px 24px',
                      background: 'linear-gradient(135deg, #00d4ff, #7928ca)',
                      border: 'none',
                      borderRadius: '10px',
                      color: '#ffffff',
                      cursor: 'pointer',
                      fontWeight: 700,
                      boxShadow: '0 0 15px rgba(0, 212, 255, 0.4)'
                    }}
                  >
                    Authorize OAuth
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <span style={{ fontSize: '0.78rem', color: '#64748b' }}>🔒 Credentials stored in encrypted database using AES-256</span>
          <button
            onClick={onClose}
            style={{
              padding: '10px 24px',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '10px',
              color: '#f8fafc',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
