# Gnosis

An AI-powered adaptive learning platform that generates personalized technical learning paths through a multi-agent system. Built with LangGraph orchestration, powered by Groq (Llama 3.3 70B & Kimi K2), with optional Tavily web search integration.

## Overview

Transforms any technical learning goal into a structured curriculum with interactive challenges, AI evaluation, and adaptive hints.

**Key Features:**
- Dynamic learning path generation (2-6 modules, 5-8 challenges each)
- Experience level adaptation (Beginner/Intermediate/Advanced)
- AI-powered evaluation without code execution
- Progressive 3-level hint system
- Persistent progress tracking with session resumption

## Architecture

### Tech Stack

**Backend:**
- FastAPI - REST API
- LangGraph - Agent orchestration with checkpointing
- LangChain - LLM framework
- Groq (Llama 3.3 70B, Kimi K2) - Primary LLMs
- Tavily - Optional web search
- SQLite - Dual database (app data + checkpoints)

**Frontend:**
- React 18 + Vite
- Monaco Editor - Code editing
- React Markdown - Lesson rendering

### The 6 AI Agents

**Planning Agents:**
1. **Learning Path Agent** (`learning_path_agent.py`) - Generates 2-6 module curriculum
   - Standard mode: Pure LLM reasoning
   - Enhanced mode: Tavily web search
2. **Module Planner Agent** (`module_planner_agent.py`) - Creates 5-8 micro-challenges per module

**Challenge Workflow Agents:** (`challenge_evaluation_agents.py`)
3. **Tutor Agent** (`tutor_agent.py`) - Creates personalized markdown lessons with context awareness
4. **Coding Challenge Agent** - Designs pedagogically optimized challenges (code or conceptual)
5. **Code Evaluator Agent** - Evaluates submissions without execution
6. **Remediation Agent** - Provides progressive 3-level hints on failure

### System Flow

```
User → FastAPI (app.py) → Planning Agents → LangGraph Workflow → Challenge Agents
                                ↓                                        ↓
                          learning_system.db ← Progress Tracking ← Evaluation
                                                                         ↓
                          challenge_sessions.db ← LangGraph Checkpoints
```

**Core Files:**
- `app.py` - FastAPI server with all REST endpoints
- `challenge_graph.py` - LangGraph workflow orchestration
- `challenge_state.py` - State schema for workflow
- `database/db_operations.py` - Database abstraction layer
- `database/schema.sql` - SQLite schema definitions

## User Flow

### 1. Setup (30-60s)
`POST /setup` → **Learning Path Agent** generates 2-6 modules → User reviews path

### 2. Challenge Generation (1-3min)
`POST /path/approve` → **Module Planner Agent** creates 5-8 challenges per module → Dashboard ready

### 3. Learning Loop (per challenge)
```
GET /challenge/{m}/{c} → Tutor Agent → Lesson rendered
                      → Challenge Agent → Challenge displayed
                                   ↓
User submits code → Evaluator Agent → Pass? → Next challenge
                                    → Fail? → Remediation Agent → Retry
```

**Database Schema** (`learning_system.db`):
- `user_profile` - User accounts and learning goals
- `learning_path` - Generated module structure
- `module_challenges` - Challenge roadmaps per module
- `challenge_progress` - Status tracking, cached content, submission history

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 16+
- Groq API Key
- Optional: Tavily API Key (for web search)

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key  # Optional

# Run server
python app.py  # http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Toggle Enhanced Mode
In `app.py`, set `USE_ENHANCED_LEARNING_PATH = True` to enable web search (Tavily keys)

## Project Structure

```
├── agents/
│   ├── learning_path_agent.py          # Standard learning path generation
│   ├── learning_path_agent_enhanced.py # Web search + Gemini synthesis
│   ├── module_planner_agent.py         # Challenge roadmap creation
│   ├── tutor_agent.py                  # Lesson generation
│   └── challenge_evaluation_agents.py  # Challenge/Evaluator/Remediation agents
├── database/
│   ├── db_operations.py                # Database abstraction
│   └── schema.sql                      # SQLite schema
├── documentation/
│   ├── BACKEND.md                      # API documentation
│   └── FRONTEND.md                     # Frontend guide
├── frontend/
│   ├── src/
│   │   ├── pages/                      # SetupPage, Dashboard, ChallengePage
│   │   ├── components/                 # MermaidDiagram, etc.
│   │   └── services/api.js             # Backend client
│   └── package.json
├── app.py                              # FastAPI server
├── challenge_graph.py                  # LangGraph workflow
├── challenge_state.py                  # State schema
├── requirements.txt
└── README.md
```

