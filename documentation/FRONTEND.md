# Adaptive Learning OS - Frontend

Simple, functional React frontend for the Adaptive Learning OS.

## Features

✅ **Setup Flow** - Input learning goal + experience level
✅ **Path Approval** - Review and approve generated learning path
✅ **Dashboard** - Visual progress tracking with module/challenge grid
✅ **Challenge View** - Split view with lesson (markdown) + code editor (Monaco)
✅ **Code Submission** - Real-time evaluation with remediation hints
✅ **Responsive Design** - Clean, functional UI

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool (faster than CRA)
- **React Router** - Client-side routing
- **Monaco Editor** - VS Code editor for code editing
- **React Markdown** - Markdown rendering for lessons
- **React Syntax Highlighter** - Syntax highlighting for code blocks in lessons

## Prerequisites

1. **Backend running** at `http://localhost:8000`
   ```bash
   # In parent directory
   python3 app.py
   ```

2. **Node.js** installed (v16+)

## Installation & Running

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run at: **http://localhost:5173**

## Usage Flow

1. **Setup Page** (`/`)
   - Enter learning goal (e.g., "Build REST APIs")
   - Select experience level
   - Click "Generate Learning Path"
   - Wait 30-60 seconds

2. **Path Approval** (`/approve`)
   - Review generated modules
   - Click "Approve & Generate Challenges"
   - Wait 1-3 minutes for challenge generation

3. **Dashboard** (`/dashboard`)
   - View all modules and challenges with full titles in list format
   - Green ✓ = completed, Yellow → = in progress, Gray ○ = not started
   - Click any challenge to start (all are accessible)

4. **Challenge Page** (`/challenge/{m}/{c}`)
   - **First View**: Lesson (scrollable markdown)
   - **Second View**:
     - Challenge prompt
     - Input area (adapts to challenge type):
       - **Code challenges**: Monaco Editor (dark theme, syntax highlighting)
       - **Conceptual challenges**: Clean text area (light, user-friendly)
     - Submit button
     - Evaluation results
     - Remediation hints (if failed)

5. **Submit Solution**
   - Write/edit code (code challenges) or write text (conceptual challenges)
   - Click "Submit Solution"
   - Wait 10-30 seconds for evaluation
   - If passed: Auto-redirects to dashboard in 3 seconds
   - If failed: Shows remediation hints, try again

## File Structure

```
frontend/
├── src/
│   ├── services/
│   │   └── api.js              # Backend API calls
│   ├── pages/
│   │   ├── SetupPage.jsx       # Learning goal input
│   │   ├── PathApprovalPage.jsx  # Module review
│   │   ├── Dashboard.jsx       # Progress view
│   │   └── ChallengePage.jsx   # Lesson + Editor
│   ├── App.jsx                 # Main routing
│   ├── App.css                 # Global styles
│   └── main.jsx                # Entry point
└── package.json
```

## Troubleshooting

### Backend Connection Error
- Ensure backend is running: `python3 app.py`
- Check backend URL in `src/services/api.js` (default: `http://localhost:8000`)

### Slow Loading
- Learning path generation: 30-60 seconds (normal)
- Challenge generation: 1-3 minutes for all modules (normal)
- First challenge load: 1-2 minutes (generates lesson + challenge, then caches)
- Subsequent loads: Instant (cached)

### Rate Limit Errors
- Gemini free tier: ~60 requests/minute
- Backend has auto-retry with exponential backoff
- Wait 2-3 minutes if you hit rate limit

## Development

```bash
# Development mode (hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## API Endpoints Used

- `GET /session` - Load user state
- `POST /setup` - Generate learning path
- `POST /path/approve` - Generate challenges
- `GET /challenge/{m}/{c}` - Get challenge content
- `POST /challenge/{m}/{c}/submit` - Submit code
- `GET /progress` - Get progress summary

## Notes

- **Single user MVP**: No authentication required
- **No backend changes needed**: Frontend connects to existing API
- **Minimal dependencies**: Only essential packages
- **Functional over pretty**: Clean, usable UI without fancy animations

---

**Built with** ⚛️ React + ⚡ Vite + 🎨 Simple CSS
