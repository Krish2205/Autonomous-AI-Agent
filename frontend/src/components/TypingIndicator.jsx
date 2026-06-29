import React from 'react';

const AGENT_EMOJIS = {
  search: '🔍',
  code: '💻',
  analyse: '📊',
  summary: '📝',
  email: '📧',
  database: '🗄️',
  scraper: '🌐',
  agent_builder: '🔧',
  calendar: '📅',
  devops: '⚙️',
  finance: '💵',
  image_gen: '🎨',
  maps: '🗺️',
  notification: '🔔',
  package_manager: '📦',
  translation: '🗣️',
  video_to_mp3: '🎬',
  visualization: '📈',
  voice: '🎙️',
  cloud_infra: '☁️',
  github_workflow: '🔀',
  market_intelligence: '📊',
  financial_reporting: '📑',
  sec_ops: '🛡️',
  compliance: '📜',
  biomedical_rag: '🧬',
  marketing_campaign: '📣',
  multimedia_processor: '🎞️',
  legal_contract: '⚖️',
  talent_ops: '👔'
};

export default function TypingIndicator({ currentStep }) {
  const agentName = currentStep?.agent ? currentStep.agent.toLowerCase() : null;
  const emoji = agentName && AGENT_EMOJIS[agentName] ? AGENT_EMOJIS[agentName] : '🤖';
  const displayAgent = currentStep?.agent ? currentStep.agent.toUpperCase().replace(/_/g, ' ') : null;
  const thought = currentStep?.thought || currentStep?.query || null;

  return (
    <div className="typing-indicator" id="typing-indicator">
      <div className="typing-avatar glowing-avatar">{emoji}</div>
      <div className="typing-bubble dynamic-process-bubble">
        <div className="typing-header">
          <div className="typing-dots">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
          <span className="typing-label">
            {displayAgent ? (
              <>Executing <strong className="agent-badge">{displayAgent}</strong> Agent...</>
            ) : (
              'JARVIS is reasoning & planning...'
            )}
          </span>
        </div>

        {thought && (
          <div className="step-thought-container">
            <span className="thought-icon">💡</span>
            <span className="thought-text">{thought}</span>
          </div>
        )}

        <div className="process-progress-bar">
          <div className="process-progress-fill" />
        </div>
      </div>
    </div>
  );
}
