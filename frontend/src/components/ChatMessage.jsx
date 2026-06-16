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
