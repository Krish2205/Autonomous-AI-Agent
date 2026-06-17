import React from 'react';
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

  // Curated color palette matching our variables
  const colors = [
    '#00d4ff', // Cyan
    '#7c3aed', // Violet
    '#22c55e', // Emerald
    '#f43f5e', // Rose
    '#f59e0b', // Amber
    '#3b82f6', // Blue
  ];

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={11} />
            <YAxis stroke="#8b8fad" fontSize={11} />
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
                strokeWidth={2.5}
                activeDot={{ r: 6 }}
              />
            ))}
            {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />}
          </LineChart>
        );
      case 'area':
        return (
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={11} />
            <YAxis stroke="#8b8fad" fontSize={11} />
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
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={4}
              dataKey={pieKey}
              nameKey={xKey}
            >
              {data.map((entry, index) => (
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
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={11} />
            <YAxis stroke="#8b8fad" fontSize={11} />
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
                dot={{ r: 6, strokeWidth: 2 }}
                activeDot={{ r: 8 }}
              />
            ))}
            {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />}
          </LineChart>
        );
      case 'bar':
      default:
        return (
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(100, 120, 255, 0.1)" />
            <XAxis dataKey={xKey} stroke="#8b8fad" fontSize={11} />
            <YAxis stroke="#8b8fad" fontSize={11} />
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
      {title && (
        <h4
          style={{
            margin: '0 0 16px 0',
            fontSize: '1.05rem',
            fontWeight: 650,
            background: 'linear-gradient(135deg, #00d4ff, #7c3aed)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          {title}
        </h4>
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

  return (
    <div className={`message ${isUser ? 'user' : 'jarvis'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div>
        <div className="message-content">
          {parseMarkdown(content)}
        </div>
        <div className="message-timestamp">
          {formatTimestamp(timestamp)}
        </div>
      </div>
    </div>
  );
}
