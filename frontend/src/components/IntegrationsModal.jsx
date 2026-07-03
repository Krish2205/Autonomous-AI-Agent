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
  const [testingKey, setTestingKey] = useState(null);

  const handleTestConnection = async (key, service) => {
    setTestingKey(key);
    try {
      const userToken = getActiveUserToken();
      const res = await fetch('/api/auth/integrations/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`
        },
        body: JSON.stringify({ provider: key })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        if (onToast) onToast({ level: 'success', title: 'Connection Active', message: data.message || 'Connection verified successfully!' });
      } else {
        if (onToast) onToast({ level: 'error', title: 'Connection Failed', message: data.detail || data.message || 'Connection check failed.' });
      }
    } catch (err) {
      if (onToast) onToast({ level: 'error', title: 'Verification Error', message: `Failed to verify: ${err.message}` });
    } finally {
      setTestingKey(null);
    }
  };

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

  // Listen for message events from the OAuth popup
  useEffect(() => {
    const handleOAuthMessage = (event) => {
      if (event.data && event.data.type === 'oauth_success') {
        const { provider, email } = event.data;
        setIntegrations(prev => ({
          ...prev,
          [provider]: {
            ...prev[provider],
            connected: true,
            account: email
          }
        }));
        if (onToast) onToast({ level: 'success', title: 'OAuth Verified & Connected!', message: `Successfully authenticated ${provider} as ${email}.` });
      }
    };

    window.addEventListener('message', handleOAuthMessage);
    return () => {
      window.removeEventListener('message', handleOAuthMessage);
    };
  }, [onToast]);

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
      const token = getActiveUserToken();
      if (key === 'google_workspace') {
        try {
          const res = await fetch(`/api/auth/google/url?session_token=${token}`);
          const data = await res.json();
          if (data.oauth_url) {
            if (onToast) onToast({ level: 'info', title: 'Redirecting to Google...', message: 'Opening Google OAuth authorization page.' });
            
            // Open Google OAuth in a popup window
            const width = 600;
            const height = 650;
            const left = window.screen.width / 2 - width / 2;
            const top = window.screen.height / 2 - height / 2;
            window.open(
              data.oauth_url,
              'Google OAuth',
              `width=${width},height=${height},left=${left},top=${top}`
            );
            return;
          }
        } catch (err) {
          console.error("Failed to fetch Google OAuth URL:", err);
        }
      } else {
        // Open credentials popup window
        const width = 500;
        const height = 550;
        const left = window.screen.width / 2 - width / 2;
        const top = window.screen.height / 2 - height / 2;
        window.open(
          `/api/auth/popup/${key}?session_token=${token}`,
          `Connect ${service.name}`,
          `width=${width},height=${height},left=${left},top=${top}`
        );
      }
    }
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

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {item.connected && (
                  <button
                    onClick={() => handleTestConnection(key, item)}
                    disabled={testingKey === key}
                    style={{
                      padding: '9px 18px',
                      borderRadius: '10px',
                      fontWeight: 700,
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      border: '1px solid rgba(0, 212, 255, 0.4)',
                      background: 'rgba(0, 212, 255, 0.08)',
                      color: '#00d4ff',
                      transition: 'all 0.2s ease',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {testingKey === key ? 'Verifying...' : '⚡ Test Connection'}
                  </button>
                )}
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
            </div>
          ))}
        </div>


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
