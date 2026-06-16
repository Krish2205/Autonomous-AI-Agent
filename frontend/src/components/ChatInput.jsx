import { useState, useRef, useEffect } from 'react';

const SUGGESTED_PROMPTS = [
  "Search for the latest AI news",
  "Summarize a document for me",
  "Write a Python function to sort a list",
  "Check my recent emails",
  "Analyze my uploaded documents",
];

export default function ChatInput({ onSend, onUpload, isLoading, isUploading, showSuggestions }) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 150) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || isUploading) return;
    onSend(trimmed);
    setInput('');
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (prompt) => {
    if (isLoading || isUploading) return;
    onSend(prompt);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file || !onUpload) return;
    onUpload(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="chat-input-area" id="chat-input-area">
      {showSuggestions && (
        <div className="prompt-chips" style={{ marginBottom: '16px', justifyContent: 'flex-start' }}>
          {SUGGESTED_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              className="prompt-chip"
              onClick={() => handleChipClick(prompt)}
              disabled={isLoading || isUploading}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-wrapper">
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileChange}
          accept=".txt,.md,.pdf,.docx,.pptx,.png,.jpg,.jpeg"
        />

        <button
          type="button"
          className="upload-btn"
          id="upload-button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading || isUploading}
          aria-label="Upload document"
          title="Upload document (.pdf, .docx, .pptx, .txt, .png, .jpg)"
        >
          {isUploading ? (
            <div className="upload-spinner" />
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '18px', height: '18px' }}>
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          )}
        </button>

        <textarea
          ref={textareaRef}
          className="chat-input"
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isUploading ? "Uploading & indexing document..." : "Ask JARVIS anything..."}
          rows={1}
          disabled={isLoading || isUploading}
        />
        <button
          className="send-btn"
          id="send-button"
          onClick={handleSend}
          disabled={!input.trim() || isLoading || isUploading}
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      <div className="input-hint">
        Press <strong>Enter</strong> to send · <strong>Shift + Enter</strong> for new line
      </div>
    </div>
  );
}
