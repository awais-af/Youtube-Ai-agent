# 🎓 Awais(YT) Ai Agent

An intelligent, interactive AI agent designed for developers, students, and engineers to turn any YouTube video tutorial into an interactive personal coding tutor.

Powered by **Groq** (ultra-fast inference with Llama 3.3 70B) with dual-engine support for **OpenAI** (GPT-4o / GPT-4o-mini).

---

## ✨ Features

- **🎯 Any YouTube Video Tutorial Ingestion**:
  - Supports standard URLs (`watch?v=...`), short links (`youtu.be/...`), embed URLs, and Shorts.
  - Automatically fetches video metadata (title, instructor/channel, thumbnail) with zero API keys required.
- **⏱️ Timestamped Transcript Processing**:
  - Automatically fetches full transcripts with timestamps using `youtube-transcript-api`.
  - Intelligently chunks transcript into time-aligned semantic blocks with exact timestamps (`[MM:SS]`).
  - The AI tutor cites exact video timestamps so you can jump to that exact second in the video!
- **💬 Interactive Tutor & Multi-Turn Chat**:
  - Ask any technical question or request clarification about anything taught in the video.
  - Streaming responses with real-time feedback.
- **🗺️ Tutorial Roadmap & Syllabus**:
  - Automatically synthesizes an executive summary, learning objectives, prerequisites, and a chronological module-by-module breakdown.
- **💻 Code, Terminal Commands & Architecture Extractor**:
  - Extracts and reconstructs runnable code snippets, configuration files, shell commands, and syntax patterns demonstrated in the video.
- **📝 Study Guide & Cheatsheet Generator**:
  - Generates core concept definitions, quick reference sheets, FAQs, and 3-minute flashcards.
- **🧠 Mastery Quiz & Hands-on Coding Challenge**:
  - Auto-generates multiple-choice questions with timestamped explanations and hands-on mini projects.
- **🔍 Live Internet Fact Check (DuckDuckGo + Groq AI)**:
  - Automatically identifies perishable technical claims (commands, package versions, APIs, and syntax).
  - Uses live DuckDuckGo search (zero API keys needed) and Groq LLM (temperature 0) to verify validity.
  - Badges each claim as **✅ Still Valid**, **⚠️ Outdated**, or **❓ Unverified**, giving modern replacements and source links.
- **📄 Downloadable Comprehensive PDF Report**:
  - Exports a professional, clean multi-page PDF summarizing the video overview, roadmap, quiz, and fact check audit.
- **⚡ Dual LLM Provider Engine**:
  - **Groq** (Default & Recommended): Blazing fast inference using `llama-3.3-70b-versatile` or `qwen/qwen3.8-27b`.
  - **OpenAI**: High-precision reasoning using `gpt-4o` or `gpt-4o-mini`.


---

## 📁 Project Architecture

```
youtube-tutorial-agent/
│
├── .env.example                     # Environment template for API keys
├── .env                             # Local config file
├── requirements.txt                 # Dependencies
├── app.py                           # Modern Streamlit Web Application
├── cli.py                           # Rich Command Line Interface
├── example_usage.py                 # Python API demonstration script
├── test_agent.py                    # Unit tests
│
└── yt_agent/                        # Core Agent Package
    ├── __init__.py                  # Package exports
    ├── config.py                    # Global configurations & model definitions
    ├── extractor.py                 # YouTube URL parsing, metadata & transcript extraction
    ├── transcript_processor.py      # Timestamp chunking, duration calculations & search
    ├── llm_provider.py              # Unified Groq & OpenAI completion/streaming client
    ├── prompts.py                   # Specialized tutorial and tutoring prompts
    └── agent.py                     # YouTubeTutorialAgent brain & orchestration
```

---

## 🚀 Quickstart

### 1. Configure API Keys
Create a `.env` file (or copy from `.env.example`):
```env
# Groq API Key (Recommended - Get yours at https://console.groq.com/keys)
GROQ_API_KEY=your_groq_api_key_here

# OpenAI API Key (Optional - Get yours at https://platform.openai.com/api-keys)
OPENAI_API_KEY=your_openai_api_key_here

DEFAULT_LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
```

*(Note: You can also enter or switch API keys directly inside the Streamlit Web UI or via the CLI flag).*

---

### 2. Run the Streamlit Web Application

Launch the modern glassmorphism web interface:

```bash
streamlit run app.py
```

Features in the Web UI:
- **Video Player**: Embedded video player to watch the video alongside the agent.
- **Interactive Chat**: Stream responses with quick question chips.
- **Roadmap Tab**: Chronological syllabus ready to download as `.md`.
- **Code Extractor Tab**: Extracted runnable code snippets with download options.
- **Study Notes Tab**: Cheatsheets and flashcards.
- **Quiz Tab**: Interactive self-testing quiz.
- **Transcript Search**: Search keywords to jump to exact timestamps.

---

### 3. Run via Command Line (CLI)

Use the interactive terminal CLI powered by `rich`:

```bash
# Interactive Chat Mode
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode chat

# Extract Code & Commands
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode code

# Generate Syllabus / Roadmap
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode curriculum

# Generate Study Notes
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode notes

# Generate Mastery Quiz
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode quiz

# Live Internet Fact Check (Audits Technical Claims)
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode factcheck

# Export Full PDF Report (with Fact Check)
python cli.py --url "https://www.youtube.com/watch?v=kqtD5dpn9C8" --mode pdf
```

---

### 4. Use as a Python Library in Your AI Projects

As a Python & AI engineer, you can import and control the agent in your own scripts:

```python
from yt_agent import YouTubeTutorialAgent

# Initialize Agent
agent = YouTubeTutorialAgent(provider="groq", model="llama-3.3-70b-versatile")

# Ingest Video
agent.load_video("https://www.youtube.com/watch?v=kqtD5dpn9C8")

# 1. Ask a question with streaming output
for chunk in agent.explain("Explain how variables work in this tutorial", stream=True):
    print(chunk, end="", flush=True)

# 2. Extract runnable code
code_guide = agent.extract_code()
print(code_guide)

# 3. Generate structured syllabus
curriculum = agent.generate_curriculum()
print(curriculum)

# 4. Search transcript for exact moments
matches = agent.search_transcript("while loop")
for match in matches:
    print(f"Timestamp: {match['timestamp']} -> {match['text']}")
```

---

## 🧪 Running Tests

To verify that URL parsing, transcript processing, and metadata extraction work properly:

```bash
python test_agent.py
```
