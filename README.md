# 🤖 JARVIS — Autonomous AI Operating System

JARVIS is a highly modular, extensible, multi-agent AI operating system powered by LangChain and Groq. 

Unlike traditional orchestrators that run agents in static parallel paths, JARVIS features a **sequential agentic loop (ReAct pattern)**. The central planner reasons step-by-step using a persistent reasoning scratchpad, executing specialized agents sequentially and feeding their outputs forward to solve complex, multi-stage requests.

---

## 🏗️ System Architecture

```
                                 ┌────────────────────────┐
                                 │     React Frontend     │
                                 └───────────┬────────────┘
                                             │ (FastAPI REST & upload)
                                             ▼
                                 ┌────────────────────────┐
                                 │     FastAPI Server     │
                                 └───────────┬────────────┘
                                             │
                                             ▼
                                ┌──────────────────────────┐
                                │ Conversation Memory      │
                                └────────────┬─────────────┘
                                             │ (Context)
                                             ▼
                                ┌──────────────────────────┐
                  ┌────────────►│  Planner LLM (Llama 70B) ├────────────┐
                  │             └────────────┬─────────────┘            │
                  │                          │                          │
            (Scratchpad)                     │ (Next Step Decision)     │
                  │                          ▼                          │
                  │             ┌──────────────────────────┐            │
                  └─────────────┤   Agent Pool Registry    │            │
                                ├──────────────────────────┤            │
                                │ 🔍 Search Agent          │            │
                                │ 💻 Code Agent (Sandbox)  │            │
                                │ 📊 Analyse Agent (RAG)   │            │
                                │ 📝 Summary Agent         │            │
                                │ 📧 Email Agent (Gmail)   │            │
                                │ 🗄️ Database Agent (SQL)  │            │
                                │ 🌐 Scraper Agent (HTML)  │            │
                                └────────────┬─────────────┘            │
                                             │                          │
                                             ▼ (All Steps Complete)     │
                                ┌──────────────────────────┐            │
                                │    Synthesizer LLM       │◄───────────┘
                                └────────────┬─────────────┘
                                             │
                                             ▼
                                ┌──────────────────────────┐
                                │   Final User Response    │
                                └──────────────────────────┘
```

---

## ⚡ Key Features

* **Sequential Agentic Loop:** Solves queries step-by-step. If you ask to *"Search for the price of BTC, calculate buy power for $1000 in Python, and email the output,"* the planner runs `search` ➔ `code` (sandbox calculation) ➔ `email` sequentially.
* **7 Core Plug-and-Play Agents:**
  1. **🔍 Search:** Real-time web searches using Tavily API.
  2. **💻 Code:** Sandbox file operations (read/write/search) in a secure workspace.
  3. **📊 Analyse:** Document RAG over local files. Images are natively analyzed using **Llama 4 Scout** (multimodal vision LLM).
  4. **📝 Summary:** Contextual text summaries and general writing.
  5. **📧 Email:** Read inbox summaries, fetch emails, and send messages via Gmail SMTP/IMAP.
  6. **🗄️ Database:** Create tables, insert records, and query a local SQLite database (`jarvis.db`) using natural-language-to-SQL translation.
  7. **🌐 Scraper:** Fetch webpage contents and strip scripts/styles/navigation to extract clean body text.
* **Aesthetic React Dashboard UI:**
  * **Agent Execution Visualizer:** Registry cards glow with a breathing neon outline and display active indicators when selected during loop executions.
  * **Interactive File Upload:** Drag-and-drop or select documents (PDFs, images, docx, etc.) directly in the chat to auto-index them in the FAISS vector database.
  * **Session Memory Sync:** Unique session tracking across multiple chats to isolate references.

---

## 📁 Project Structure

```
JARVIS/
├── main.py                       # CLI Wrapper
├── requirements.txt              # Python Dependencies
├── README.md                     # Documentation
│
├── backend/                      # Python Server-Side Code
│   ├── main.py                   # CLI Core Interface
│   ├── config.py                 # Central configurations (LLMs, paths)
│   ├── logger.py                 # Color-coded structured logs
│   │
│   ├── core/                     # Orchestrator Brain
│   │   ├── orchestrator.py       # Sequential planning loop controller
│   │   ├── planner.py            # Step-by-step tool selector
│   │   ├── synthesizer.py        # Final compiler
│   │   └── memory.py             # Conversation history manager
│   │
│   ├── agents/                   # Modular Agent Pool
│   │   ├── base.py               # Abstract Base Agent
│   │   ├── search_agent.py       # Tavily Web Search
│   │   ├── code_agent.py         # File operations
│   │   ├── analyse_agent.py      # Vector DB RAG
│   │   ├── summary_agent.py      # General language tasks
│   │   ├── email_agent.py        # Gmail IMAP/SMTP integration
│   │   ├── database_agent.py     # SQLite Database Agent
│   │   └── scraper_agent.py      # HTML Scraper Agent
│   │
│   ├── tools/                    # Shared Utilities
│   │   └── document_loader.py    # Text, PDF, Word, Image vision parser
│   │
│   └── api/                      # FastAPI App
│       └── server.py             # REST routes (/query, /upload, /health)
│
└── frontend/                     # Vite + React Client Dashboard
    ├── src/
    │   ├── App.jsx               # Main controller
    │   ├── index.css             # Glassmorphism & Neon styles
    │   └── components/           # UI Layout components
    └── vite.config.js
```

---

## 🚀 Setup & Installation

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/yourusername/JARVIS.git
cd JARVIS
```

Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
GMAIL_EMAIL=your_gmail_address
GMAIL_APP_PASSWORD=your_gmail_app_password
```

### 2. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
```

---

## 📡 Running Locally

### Start Backend Server (FastAPI)
In the root directory, run:
```bash
uvicorn backend.api.server:app --reload --port 8000
```

### Start Frontend Server (Vite)
In the `frontend/` directory, run:
```bash
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) to interact with the dashboard.

---

## 📅 Future Roadmap

We plan to expand JARVIS's OS capabilities with the following phases:

* **Phase 2 — Domain Specific Agents:**
  * 💰 **Finance Agent:** Fetch stock prices, portfolio metrics, and crypto trends.
  * 📅 **Calendar Agent:** Google Calendar scheduler to check free slots and book meetings.
  * 📱 **Social Media Agent:** Draft and schedule posts (Twitter/X, LinkedIn) directly.
* **Phase 3 — Orchestration & Scalability:**
  * 🔄 **Self-Correction Loops:** Allow agents to reflect on errors (like failing tests or bad SQL) and auto-correct before reporting back.
  * 🔐 **Multi-User Auth:** Add Clerk or Supabase authentication to support multiple separate user spaces.
* **Phase 4 — Interface & Integrations:**
  * 🗣️ **Voice Interface:** Native Speech-to-Text (STT) and Text-to-Speech (TTS) integration.
  * 🔌 **Plugin Marketplace:** Allow third-party Python packages to be added as agents dynamically from a metadata configuration file.

---

## 📜 License

This project is licensed under the MIT License.
