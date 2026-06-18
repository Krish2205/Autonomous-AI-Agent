import { useState, useEffect } from 'react';

export default function DevPanel({ sessionToken, userId, onClose }) {
  const [activeTab, setActiveTab] = useState('analytics');
  
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

  // Fetch all necessary data
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
      } else {
        const [outRes, incRes] = await Promise.all([
          fetch('/api/webhooks/outgoing', { headers }),
          fetch('/api/webhooks/incoming/logs', { headers })
        ]);
        
        if (outRes.ok) setOutgoingHooks(await outRes.json());
        if (incRes.ok) setIncomingLogs(await incRes.json());
      }
    } catch (err) {
      console.error("Failed to load developer stats:", err);
      setErrorMsg("Failed to fetch data from backend. Make sure the server is online.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, sessionToken]);

  // Handle outgoing webhook submission
  const handleAddWebhook = async (e) => {
    e.preventDefault();
    if (!newHookName.trim() || !newHookUrl.trim()) return;
    
    setErrorMsg('');
    try {
      const res = await fetch('/api/webhooks/outgoing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          name: newHookName.trim(),
          url: newHookUrl.trim(),
          service: newHookService
        })
      });
      
      if (res.ok) {
        setNewHookName('');
        setNewHookUrl('');
        setNewHookService('slack');
        fetchData();
      } else {
        const err = await res.json().catch(() => null);
        setErrorMsg(err?.detail || "Failed to configure outgoing webhook.");
      }
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  // Handle outgoing webhook delete
  const handleDeleteWebhook = async (id) => {
    if (!window.confirm("Are you sure you want to delete this outgoing webhook?")) return;
    try {
      const res = await fetch(`/api/webhooks/outgoing/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  // Generate unique incoming webhook URL
  const getIncomingUrl = (source) => {
    const origin = window.location.origin;
    return `${origin}/api/webhooks/incoming/${userId}/${source}`;
  };

  return (
    <div className="dev-panel-overlay">
      <style>{`
        .dev-panel-overlay {
          position: fixed;
          inset: 0;
          z-index: 900;
          background: rgba(4, 4, 12, 0.7);
          backdrop-filter: blur(15px);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #e8eaff;
          font-family: 'Inter', system-ui, sans-serif;
        }
        
        .dev-card {
          width: 850px;
          height: 650px;
          background: rgba(12, 12, 35, 0.75);
          border: 1px solid rgba(100, 120, 255, 0.15);
          border-radius: 20px;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 212, 255, 0.05);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          position: relative;
        }

        .dev-header {
          padding: 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .dev-title-area {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .dev-icon {
          font-size: 1.6rem;
        }

        .dev-title {
          font-size: 1.25rem;
          font-weight: 800;
          letter-spacing: 2px;
          background: linear-gradient(135deg, #00d4ff, #7c3aed);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .dev-close-btn {
          background: none;
          border: none;
          color: #8b8fad;
          font-size: 1.5rem;
          cursor: pointer;
          transition: color 0.2s;
        }

        .dev-close-btn:hover {
          color: #ff4a6b;
        }

        .dev-nav {
          display: flex;
          padding: 0 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          gap: 24px;
          background: rgba(0, 0, 0, 0.15);
        }

        .nav-tab {
          padding: 16px 8px;
          font-size: 0.85rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #8b8fad;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          transition: all 0.2s;
        }

        .nav-tab.active {
          color: #00d4ff;
          border-bottom-color: #00d4ff;
        }

        .dev-body {
          flex: 1;
          padding: 24px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .dev-error {
          padding: 12px;
          background: rgba(244, 63, 94, 0.1);
          border: 1px solid rgba(244, 63, 94, 0.2);
          border-radius: 8px;
          color: #f43f5e;
          font-size: 0.8rem;
        }

        /* Analytics Grid style */
        .analytics-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
        }

        .metric-card {
          padding: 16px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          text-align: center;
        }

        .metric-label {
          font-size: 0.7rem;
          color: #8b8fad;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 8px;
        }

        .metric-value {
          font-size: 1.4rem;
          font-weight: 700;
          color: #00d4ff;
        }

        .section-title {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 1.5px;
          color: #a78bfa;
          margin-bottom: 12px;
          font-weight: 700;
          border-left: 2px solid #a78bfa;
          padding-left: 8px;
        }

        /* Webhook / Config style */
        .webhook-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          padding: 16px;
        }

        .webhook-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .webhook-row:last-child {
          border-bottom: none;
        }

        .webhook-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .webhook-name {
          font-weight: 600;
          font-size: 0.9rem;
        }

        .webhook-url {
          font-size: 0.75rem;
          color: #8b8fad;
          font-family: monospace;
        }

        .webhook-service-badge {
          display: inline-block;
          padding: 2px 6px;
          font-size: 0.6rem;
          background: rgba(124, 58, 237, 0.2);
          border: 1px solid rgba(124, 58, 237, 0.3);
          color: #a78bfa;
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: bold;
          align-self: flex-start;
        }

        .webhook-del-btn {
          background: rgba(244, 63, 94, 0.1);
          border: 1px solid rgba(244, 63, 94, 0.2);
          color: #f43f5e;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .webhook-del-btn:hover {
          background: rgba(244, 63, 94, 0.25);
          border-color: #f43f5e;
        }

        .webhook-form {
          display: grid;
          grid-template-columns: 1fr 2fr 1fr auto;
          gap: 12px;
          align-items: end;
        }

        .form-label {
          display: block;
          font-size: 0.7rem;
          color: #8b8fad;
          text-transform: uppercase;
          margin-bottom: 6px;
        }

        .form-input, .form-select {
          width: 100%;
          padding: 8px 12px;
          background: rgba(0, 0, 0, 0.3);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          color: white;
          font-size: 0.8rem;
          outline: none;
        }

        .form-input:focus, .form-select:focus {
          border-color: #00d4ff;
        }

        .add-btn {
          padding: 8px 16px;
          background: rgba(0, 212, 255, 0.15);
          border: 1px solid rgba(0, 212, 255, 0.3);
          color: #00d4ff;
          border-radius: 8px;
          font-weight: 700;
          font-size: 0.8rem;
          cursor: pointer;
          height: 34px;
        }

        .add-btn:hover {
          background: rgba(0, 212, 255, 0.3);
          border-color: #00d4ff;
        }

        /* Table styles */
        .analytics-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.8rem;
        }

        .analytics-table th, .analytics-table td {
          padding: 10px;
          text-align: left;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .analytics-table th {
          color: #8b8fad;
          font-weight: 600;
          text-transform: uppercase;
          font-size: 0.7rem;
          letter-spacing: 0.5px;
        }

        .copy-url-btn {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #a78bfa;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 0.65rem;
          cursor: pointer;
          margin-left: 8px;
        }

        .copy-url-btn:hover {
          background: rgba(124, 58, 237, 0.2);
          border-color: #a78bfa;
        }
      `}</style>

      <div className="dev-card">
        <div className="dev-header">
          <div className="dev-title-area">
            <span className="dev-icon">⚙️</span>
            <h3 className="dev-title">Developer & Webhook Hub</h3>
          </div>
          <button className="dev-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="dev-nav">
          <button
            className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            Usage & Analytics
          </button>
          <button
            className={`nav-tab ${activeTab === 'webhooks' ? 'active' : ''}`}
            onClick={() => setActiveTab('webhooks')}
          >
            Webhook Integration
          </button>
        </div>

        <div className="dev-body">
          {errorMsg && <div className="dev-error">{errorMsg}</div>}
          
          {isLoading && <div style={{ color: '#00d4ff', fontSize: '0.9rem' }}>Reloading console...</div>}

          {activeTab === 'analytics' ? (
            <>
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
                <h4 className="section-title">Query Step Performance Breakdown</h4>
                <div className="webhook-card">
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Execution Step</th>
                        <th>Total Tokens</th>
                        <th>Estimated Cost</th>
                        <th>Avg Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary?.breakdown_by_step?.map((step, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 'bold' }}>{step.step_name}</td>
                          <td>{step.total_tokens.toLocaleString()}</td>
                          <td style={{ color: '#34d399' }}>${step.estimated_cost_usd.toFixed(6)}</td>
                          <td>{step.avg_latency_ms.toFixed(1)}ms</td>
                        </tr>
                      )) || (
                        <tr>
                          <td colSpan="4" style={{ textAlign: 'center', color: '#8b8fad' }}>No records logged yet.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="section-title">Recent LLM Executions History</h4>
                <div className="webhook-card" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Step</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                        <th>Latency</th>
                        <th>Time</th>
                      </tr>
                    </thead>
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
                      )) || (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', color: '#8b8fad' }}>No history records yet.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <h4 className="section-title">Configure Outgoing Webhooks</h4>
                <div className="webhook-card" style={{ marginBottom: '16px' }}>
                  <form onSubmit={handleAddWebhook} className="webhook-form">
                    <div>
                      <label className="form-label">Name</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. Slack General"
                        value={newHookName}
                        onChange={(e) => setNewHookName(e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <label className="form-label">Webhook URL</label>
                      <input
                        type="url"
                        className="form-input"
                        placeholder="https://hooks.slack.com/services/..."
                        value={newHookUrl}
                        onChange={(e) => setNewHookUrl(e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <label className="form-label">Service Type</label>
                      <select
                        className="form-select"
                        value={newHookService}
                        onChange={(e) => setNewHookService(e.target.value)}
                      >
                        <option value="slack">Slack</option>
                        <option value="discord">Discord</option>
                        <option value="generic">Generic JSON API</option>
                      </select>
                    </div>
                    <button type="submit" className="add-btn">Configure Hook</button>
                  </form>
                </div>

                <div className="webhook-card">
                  {outgoingHooks.length > 0 ? (
                    outgoingHooks.map((hook) => (
                      <div key={hook.id} className="webhook-row">
                        <div className="webhook-info">
                          <span className="webhook-name">{hook.name}</span>
                          <span className="webhook-url">{hook.url}</span>
                          <span className="webhook-service-badge">{hook.service}</span>
                        </div>
                        <button
                          className="webhook-del-btn"
                          onClick={() => handleDeleteWebhook(hook.id)}
                        >
                          Delete
                        </button>
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: 'center', color: '#8b8fad', fontSize: '0.8rem' }}>No outgoing webhook endpoints configured yet.</div>
                  )}
                </div>
              </div>

              <div>
                <h4 className="section-title">Unique Incoming Triggers URLs</h4>
                <div className="webhook-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <label className="form-label" style={{ marginBottom: '4px' }}>GitHub Hook URL</label>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <input type="text" className="form-input" readOnly value={getIncomingUrl('github')} style={{ fontFamily: 'monospace', flex: 1 }} />
                      <button className="copy-url-btn" onClick={() => { navigator.clipboard.writeText(getIncomingUrl('github')); alert('Copied GitHub webhook URL!'); }}>Copy</button>
                    </div>
                  </div>
                  <div>
                    <label className="form-label" style={{ marginBottom: '4px' }}>Stripe Hook URL</label>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <input type="text" className="form-input" readOnly value={getIncomingUrl('stripe')} style={{ fontFamily: 'monospace', flex: 1 }} />
                      <button className="copy-url-btn" onClick={() => { navigator.clipboard.writeText(getIncomingUrl('stripe')); alert('Copied Stripe webhook URL!'); }}>Copy</button>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="section-title">Recent Incoming Webhook logs</h4>
                <div className="webhook-card" style={{ maxHeight: '150px', overflowY: 'auto' }}>
                  <table className="analytics-table">
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Payload Summary</th>
                        <th>Time Received</th>
                      </tr>
                    </thead>
                    <tbody>
                      {incomingLogs.map((log) => (
                        <tr key={log.id}>
                          <td style={{ fontWeight: 'bold', textTransform: 'uppercase' }}>{log.source}</td>
                          <td style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#8b8fad' }}>{log.payload.substring(0, 100)}...</td>
                          <td>{new Date(log.timestamp).toLocaleTimeString()}</td>
                        </tr>
                      )) || (
                        <tr>
                          <td colSpan="3" style={{ textAlign: 'center', color: '#8b8fad' }}>No logs recorded yet.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
