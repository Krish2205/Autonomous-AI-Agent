import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

/**
 * ChatMessage — Renders a single message bubble.
 * Supports basic markdown-like formatting:
 *   - **bold** → <strong>
 *   - `inline code` → <code>
 *   - ```code blocks``` → <pre><code>
 *   - - list items → <li>
 *   - numbered lists → <li>
 *   - headings (### text) → <strong>
 */

function formatTimestamp(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function parseMarkdown(text) {
  if (!text) return '';

  // Split by code blocks first
  const parts = text.split(/(```[\s\S]*?```)/g);

  return parts.map((part, i) => {
    // Code block
    if (part.startsWith('```') && part.endsWith('```')) {
      const inner = part.slice(3, -3);
      // Remove language identifier on first line if present
      const lines = inner.split('\n');
      const firstLine = lines[0].trim();
      const isLangTag = firstLine && !firstLine.includes(' ') && firstLine.length < 20;
      const code = isLangTag ? lines.slice(1).join('\n') : inner;

      if (firstLine === 'chart') {
        try {
          const chartData = JSON.parse(code.trim());
          return <InteractiveChart key={i} spec={chartData} />;
        } catch (err) {
          console.error("Failed to parse chart spec JSON", err);
          return <pre key={i}><code>{code.trim()}</code></pre>;
        }
      }

      return <pre key={i}><code>{code.trim()}</code></pre>;
    }

    // Process inline formatting
    return <span key={i}>{formatInline(part)}</span>;
  });
}

function formatInline(text) {
  const lines = text.split('\n');
  const result = [];
  let inList = false;
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      result.push(<ul key={`list-${result.length}`}>{listItems}</ul>);
      listItems = [];
      inList = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Bullet list
    if (/^[-*•]\s+/.test(trimmed)) {
      inList = true;
      const content = trimmed.replace(/^[-*•]\s+/, '');
      listItems.push(<li key={`li-${i}`}>{applyInlineStyles(content)}</li>);
      continue;
    }

    // Numbered list
    if (/^\d+[.)]\s+/.test(trimmed)) {
      inList = true;
      const content = trimmed.replace(/^\d+[.)]\s+/, '');
      listItems.push(<li key={`li-${i}`}>{applyInlineStyles(content)}</li>);
      continue;
    }

    flushList();

    // Heading
    if (/^#{1,3}\s+/.test(trimmed)) {
      const content = trimmed.replace(/^#{1,3}\s+/, '');
      result.push(
        <p key={`h-${i}`} style={{ fontWeight: 700, marginTop: '12px' }}>
          {applyInlineStyles(content)}
        </p>
      );
      continue;
    }

    // Empty line
    if (!trimmed) {
      continue;
    }

    // Regular paragraph
    result.push(<p key={`p-${i}`}>{applyInlineStyles(trimmed)}</p>);
  }

  flushList();
  return result;
}

function applyInlineStyles(text) {
  // Split by inline code, bold, and italic patterns
  const parts = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Inline code: `text`
    const codeMatch = remaining.match(/`([^`]+)`/);
    // Bold: **text** or __text__
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
    // Image: ![alt](url)
    const imgMatch = remaining.match(/!\[([^\]]*)\]\(([^)]+)\)/);

    let firstMatch = null;
    let firstIndex = remaining.length;

    if (codeMatch && codeMatch.index < firstIndex) {
      firstMatch = { type: 'code', match: codeMatch };
      firstIndex = codeMatch.index;
    }
    if (boldMatch && boldMatch.index < firstIndex) {
      firstMatch = { type: 'bold', match: boldMatch };
      firstIndex = boldMatch.index;
    }
    if (imgMatch && imgMatch.index < firstIndex) {
      firstMatch = { type: 'image', match: imgMatch };
      firstIndex = imgMatch.index;
    }

    if (!firstMatch) {
      parts.push(remaining);
      break;
    }

    // Add text before match
    if (firstIndex > 0) {
      parts.push(remaining.substring(0, firstIndex));
    }

    const m = firstMatch.match;
    if (firstMatch.type === 'code') {
      parts.push(<code key={`c-${key++}`}>{m[1]}</code>);
    } else if (firstMatch.type === 'bold') {
      parts.push(<strong key={`b-${key++}`}>{m[1]}</strong>);
    } else if (firstMatch.type === 'image') {
      parts.push(
        <img
          key={`img-${key++}`}
          src={m[2]}
          alt={m[1]}
          style={{
            maxWidth: '100%',
            borderRadius: '8px',
            marginTop: '8px',
            display: 'block',
            border: '1px solid var(--border-color, #3a2d54)'
          }}
        />
      );
    }

    remaining = remaining.substring(firstIndex + m[0].length);
  }

  return parts;
}

function InteractiveChart({ spec }) {
  const { type, title, data, xKey, yKeys, xLabel, yLabel } = spec;
  const [chartType, setChartType] = useState(type);
  const [timeline, setTimeline] = useState('All');

  // Curated color palette matching our variables
  const colors = [
    '#00d4ff', // Cyan
    '#7c3aed', // Violet
    '#22c55e', // Emerald
    '#f43f5e', // Rose
    '#f59e0b', // Amber
    '#3b82f6', // Blue
  ];

  const getFilteredData = () => {
    if (!data) return [];
    if (data.length <= 20) return data; // simple categories, no slicing

    switch (timeline) {
      case '1W':
        return data.slice(-7);
      case '1M':
        return data.slice(-30);
      case '6M':
        return data.slice(-130);
      case '1Y':
        return data.slice(-252);
      case '5Y':
        return data.slice(-1260);
      case 'All':
      default:
        return data;
    }
  };

  const filteredData = getFilteredData();

  const renderChart = () => {
    switch (chartType) {
      case 'line':
        return (
          <LineChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={10} />
            <YAxis stroke="#8b8fad" fontSize={10} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(18, 18, 50, 0.95)',
                border: '1px solid rgba(100, 120, 255, 0.25)',
                borderRadius: '8px',
                color: '#e8eaff',
                fontSize: '12px'
              }}
            />
            {yKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                dot={filteredData.length < 30 ? { r: 3 } : false}
                activeDot={{ r: 5 }}
              />
            ))}
            {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />}
          </LineChart>
        );
      case 'area':
        return (
          <AreaChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              {yKeys.map((key, index) => {
                const color = colors[index % colors.length];
                return (
                  <linearGradient key={`grad-${key}`} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.4}/>
                    <stop offset="95%" stopColor={color} stopOpacity={0.0}/>
                  </linearGradient>
                );
              })}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={10} />
            <YAxis stroke="#8b8fad" fontSize={10} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(18, 18, 50, 0.95)',
                border: '1px solid rgba(100, 120, 255, 0.25)',
                borderRadius: '8px',
                color: '#e8eaff',
                fontSize: '12px'
              }}
            />
            {yKeys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#grad-${key})`}
              />
            ))}
            {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />}
          </AreaChart>
        );
      case 'pie':
        const pieKey = yKeys[0];
        return (
          <PieChart>
            <Pie
              data={filteredData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={85}
              paddingAngle={4}
              dataKey={pieKey}
              nameKey={xKey}
            >
              {filteredData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(18, 18, 50, 0.95)',
                border: '1px solid rgba(100, 120, 255, 0.25)',
                borderRadius: '8px',
                color: '#e8eaff',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
          </PieChart>
        );
      case 'scatter':
        return (
          <LineChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={10} />
            <YAxis stroke="#8b8fad" fontSize={10} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(18, 18, 50, 0.95)',
                border: '1px solid rgba(100, 120, 255, 0.25)',
                borderRadius: '8px',
                color: '#e8eaff',
                fontSize: '12px'
              }}
            />
            {yKeys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={0}
                dot={{ r: filteredData.length < 50 ? 5 : 2, strokeWidth: 1 }}
                activeDot={{ r: 6 }}
              />
            ))}
            {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />}
          </LineChart>
        );
      case 'bar':
      default:
        return (
          <BarChart data={filteredData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={10} />
            <YAxis stroke="#8b8fad" fontSize={10} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(18, 18, 50, 0.95)',
                border: '1px solid rgba(100, 120, 255, 0.25)',
                borderRadius: '8px',
                color: '#e8eaff',
                fontSize: '12px'
              }}
            />
            {yKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
            {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />}
          </BarChart>
        );
    }
  };

  return (
    <div
      style={{
        background: 'rgba(22, 22, 54, 0.4)',
        border: '1px solid rgba(100, 120, 255, 0.15)',
        borderRadius: '16px',
        padding: '16px 20px',
        marginTop: '12px',
        marginBottom: '12px',
        maxWidth: '550px',
        width: '100%',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
        {title && (
          <h4
            style={{
              margin: 0,
              fontSize: '1rem',
              fontWeight: 650,
              background: 'linear-gradient(135deg, #00d4ff, #7c3aed)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {title}
          </h4>
        )}

        {/* Chart Type Toggles */}
        <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 0, 0.2)', padding: '2px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          {['line', 'area', 'bar', 'scatter'].map((t) => (
            <button
              key={t}
              onClick={() => setChartType(t)}
              style={{
                background: chartType === t ? 'rgba(124, 58, 237, 0.3)' : 'transparent',
                border: 'none',
                color: chartType === t ? '#00d4ff' : '#8b8fad',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                textTransform: 'capitalize',
                transition: 'all 0.2s',
                fontWeight: chartType === t ? '600' : '400'
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Slicing range selector (only show if data represents long time-series history) */}
      {data && data.length > 20 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px', marginBottom: '16px' }}>
          {['1W', '1M', '6M', '1Y', '5Y', 'All'].map((t) => (
            <button
              key={t}
              onClick={() => setTimeline(t)}
              style={{
                background: 'none',
                border: 'none',
                color: timeline === t ? '#00d4ff' : '#555876',
                padding: '2px 6px',
                cursor: 'pointer',
                fontSize: '0.7rem',
                fontWeight: timeline === t ? '700' : '500',
                borderBottom: timeline === t ? '2px solid #00d4ff' : '2px solid transparent',
                transition: 'all 0.2s'
              }}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function ChatMessage({ role, content, timestamp }) {
  const isUser = role === 'user';
  const [isPlaying, setIsPlaying] = useState(false);

  // Stop speaking on unmount
  useEffect(() => {
    return () => {
      if (isPlaying && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isPlaying]);

  const toggleSpeech = () => {
    if (!window.speechSynthesis) return;

    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
    } else {
      window.speechSynthesis.cancel();

      // Clean markdown tags out so TTS sounds natural
      let cleanText = content
        .replace(/```[\s\S]*?```/g, '') // remove code blocks
        .replace(/`([^`]+)`/g, '$1') // remove inline code backticks
        .replace(/\*\*([^*]+)\*\*/g, '$1') // remove bold formatting
        .replace(/#+\s+/g, '') // remove headers
        .replace(/[-*•]\s+/g, '') // remove list formatting
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '') // remove image tags
        .trim();

      if (!cleanText) return;

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = 'en-US';
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);

      setIsPlaying(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className={`message ${isUser ? 'user' : 'jarvis'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div>
        <div className="message-content" style={{ position: 'relative', paddingRight: !isUser ? '40px' : undefined }}>
          {parseMarkdown(content)}

          {!isUser && (
            <button
              className={`message-speaker-btn ${isPlaying ? 'playing' : ''}`}
              onClick={toggleSpeech}
              title={isPlaying ? "Stop reading" : "Read response aloud"}
              style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
              }}
            >
              {isPlaying ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px' }}>
                  <rect x="4" y="4" width="16" height="16" rx="1" ry="1" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px' }}>
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                  <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                </svg>
              )}
            </button>
          )}
        </div>
        <div className="message-timestamp">
          {formatTimestamp(timestamp)}
        </div>
      </div>
    </div>
  );
}
