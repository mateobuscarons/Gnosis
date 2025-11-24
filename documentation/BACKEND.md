# Backend API Reference - Adaptive Learning OS

**Status**: ✅ Fully Functional
**Base URL**: `http://localhost:8000`
**Tech Stack**: FastAPI + LangGraph + SQLite + 7 AI Agents (Gemini 2.5 Flash)

---

## Complete User Flow

```
1. New User → GET /session → state: "new_user"
2. User inputs goal + level → POST /setup → Learning Path generated (3-8 modules)
3. UI shows path → POST /path/approve → All module challenges generated (5-8 per module)
4. User selects challenge → GET /challenge/{m}/{c} → Lesson + Challenge displayed
5. User submits code → POST /challenge/{m}/{c}/submit → Evaluation + Remediation
6. Loop step 5 until pass → Next challenge unlocks
7. Track progress → GET /progress → Dashboard data
```

---

## API Endpoints

### 1. GET `/`
**Health check**

**Response:**
```json
{
  "status": "ok",
  "service": "Adaptive Learning OS API",
  "version": "1.0.0"
}
```

---

### 2. GET `/session`
**Load user session state**

**Response States:**
- `new_user` - No user exists, need setup
- `path_approval` - Learning path generated, awaiting approval
- `dashboard` - Ready to start challenges
- `challenge_active` - Currently in a challenge

**Response:**
```json
{
  "state": "new_user | path_approval | dashboard | challenge_active",
  "user_profile": {
    "id": 1,
    "learning_goal": "Build REST APIs with FastAPI",
    "experience_level": "Beginner",
    "created_at": "2025-11-08T10:00:00"
  },
  "learning_path": { /* Full learning path data */ },
  "current_challenge": {
    "module_number": 1,
    "challenge_number": 2,
    "status": "in_progress"
  },
  "progress_summary": { /* Progress data */ }
}
```

---

### 3. POST `/setup`
**Generate learning path (runs Learning Path Agent)**

**Request:**
```json
{
  "learning_goal": "Build a REST API with FastAPI",
  "experience_level": "Beginner | Intermediate | Advanced"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": 1,
  "learning_path": {
    "input": {
      "learning_goal": "...",
      "experience_level": "Beginner"
    },
    "learning_path": {
      "learning_goal": "Master FastAPI...",
      "modules": [
        {
          "module_number": 1,
          "title": "Python Fundamentals",
          "description": "...",
          "topics": ["Variables", "Functions", "Classes"],
          "hands_on": ["Build calculator", "Create CLI tool"]
        }
        // 3-8 modules total
      ],
      "reasoning": "Progressive path explanation"
    }
  },
  "message": "Generated 4 modules"
}
```

**Time**: ~30-60 seconds
**Rate Limit**: May retry automatically if 429 error

---

### 4. POST `/path/approve`
**Batch generate ALL module challenges (runs Module Planner Agent for each module)**

**Request:**
```json
{
  "learning_path": { /* Full learning_path object from /setup */ }
}
```

**Response:**
```json
{
  "success": true,
  "total_modules": 4,
  "total_challenges": 26,
  "message": "Learning path finalized with 26 challenges"
}
```

**Time**: ~1-3 minutes (depends on module count)
**Delays**: 10s initial + 10s between modules + exponential backoff on rate limits
**All challenges initialized as accessible (not_started status)**

---

### 5. GET `/challenge/{module_number}/{challenge_number}`
**Get challenge content (lesson + coding challenge)**

**First Time** (not cached):
- Runs: Resource Agent → Tutor Agent → Challenge Agent
- Caches: lesson_markdown + coding_challenge in database
- Time: ~1-2 minutes

**Cached**: Returns in <1 second

**Response:**
```json
{
  "lesson_markdown": "# Complete lesson in markdown...",
  "coding_challenge": {
    "challenge_format": "code | conceptual",
    "challenge_prompt": "Create a function that...",
    "starter_code": "# TODO: Your code here\ndef solution():\n    pass",
    "expected_approach": "Use list comprehension...",
    "success_criteria": [
      "Function exists and takes correct parameters",
      "Returns correct data type",
      "Handles edge cases"
    ],
    "hints_bank": [
      "Level 1: Think about iteration...",
      "Level 2: Use the range() function...",
      "Level 3: Combine range() with a list comprehension"
    ]
  },
  "challenge_data": {
    "challenge_number": 1,
    "title": "Create List Comprehension",
    "learning_objective": "...",
    "challenge_type": "implement_code",
    "difficulty": "easy"
  },
  "progress": {
    "status": "in_progress",
    "attempt_count": 0
  },
  "cached": false
}
```

---

### 6. POST `/challenge/{module_number}/{challenge_number}/submit`
**Submit code for evaluation**

**Request:**
```json
{
  "code": "def solution():\n    return [x**2 for x in range(10)]"
}
```

**Process**:
1. Resumes LangGraph workflow from checkpoint
2. Runs Code Evaluator Agent
3. If fail → Runs Remediation Agent → Returns to await_code
4. If pass → Marks complete → Unlocks next challenge

**Response (Failed):**
```json
{
  "evaluation": {
    "passed": false,
    "score": 65,
    "errors": [
      "Function doesn't handle negative inputs",
      "Missing type hints"
    ],
    "feedback": "Good structure but needs edge case handling...",
    "what_worked": [
      "Correct use of list comprehension",
      "Proper function definition"
    ],
    "what_needs_work": [
      "Add validation for negative inputs",
      "Include type hints for clarity"
    ]
  },
  "remediation": {
    "hint_level": 1,
    "targeted_hint": "Consider what happens when x is negative...",
    "encouragement": "Great use of list comprehension!",
    "key_concept_reminder": "Remember to validate inputs before processing"
  },
  "status": "needs_remediation",
  "attempt_count": 1,
  "max_attempts": 3
}
```

**Response (Passed):**
```json
{
  "evaluation": {
    "passed": true,
    "score": 95,
    "errors": [],
    "feedback": "Excellent implementation!",
    "what_worked": ["All criteria met", "Clean code"],
    "what_needs_work": []
  },
  "remediation": null,
  "status": "passed",
  "attempt_count": 2,
  "max_attempts": 3
}
```

**Time**: ~10-30 seconds
**Note**: All challenges are always accessible - no locking mechanism

---

### 7. GET `/challenges/metadata`
**Get all challenge titles and metadata for dashboard display**

**Response:**
```json
{
  "1": [
    {
      "challenge_number": 1,
      "title": "Create Basic Function",
      "learning_objective": "Understand function syntax"
    },
    {
      "challenge_number": 2,
      "title": "Add Parameters",
      "learning_objective": "Work with function parameters"
    }
  ],
  "2": [
    {
      "challenge_number": 1,
      "title": "Import Libraries",
      "learning_objective": "Learn module imports"
    }
  ]
}
```

**Keys**: Module numbers (as strings)
**Values**: Array of challenge metadata objects

**Time**: <1 second (lightweight, no lesson content)

---

### 8. GET `/progress`
**Get overall progress summary**

**Response:**
```json
{
  "modules": [
    {
      "module_number": 1,
      "total": 6,
      "completed": 3,
      "in_progress": 1,
      "locked": 2
    },
    {
      "module_number": 2,
      "total": 7,
      "completed": 0,
      "in_progress": 0,
      "locked": 7
    }
  ],
  "total_completed": 3,
  "total_challenges": 26,
  "current_challenge": {
    "user_id": 1,
    "module_number": 1,
    "challenge_number": 4,
    "status": "in_progress",
    "attempt_count": 1
  },
  "completion_percentage": 11.5
}
```

---

### 9. DELETE `/reset`
**Reset entire system (for testing)**

**Response:**
```json
{
  "success": true,
  "message": "System reset complete"
}
```

**Warning**: Deletes all databases!

---

## Database Schema

**Files:**
- `learning_system.db` - User data, paths, challenges, progress
- `challenge_sessions.db` - LangGraph checkpoints

### Tables

**user_profile**
```sql
id, learning_goal, experience_level, created_at, last_active
```

**learning_path**
```sql
id, user_id, path_json (full learning path), created_at
```

**module_challenges**
```sql
id, user_id, module_number, challenges_json (all challenges), created_at
UNIQUE(user_id, module_number)
```

**challenge_progress**
```sql
id, user_id, module_number, challenge_number,
status (locked|in_progress|completed),
lesson_markdown (cached), coding_challenge_json (cached),
attempt_count, last_submission, last_evaluation_json,
completed_at, created_at, updated_at
UNIQUE(user_id, module_number, challenge_number)
```

---

## LangGraph Workflow

**Challenge Flow:**
```
resource_agent → tutor_agent → coding_challenge_agent → **INTERRUPT**
                                                            ↓
                                                       await_code
                                                            ↓
                                                    code_evaluator
                                                            ↓
                                            route_evaluation (pass/fail)
                                                   /              \
                                              PASS: END        FAIL: remediation_agent
                                                                         ↓
                                                                   await_code (loop)
```

**Session ID Format**: `user_{user_id}_m{module}_c{challenge}`

**Checkpointing**: Full state preserved, can resume anytime

---

## Frontend Requirements

### Pages Needed

1. **Setup Page** (`/`)
   - Input: Learning goal (text)
   - Select: Experience level (Beginner/Intermediate/Advanced)
   - Button: "Generate Learning Path"
   - Shows: Loading state during generation

2. **Path Approval Page** (`/approve`)
   - Display: All generated modules (editable if needed)
   - For each module: title, description, topics, hands-on exercises
   - Button: "Approve & Generate Challenges"
   - Shows: Progress bar during batch generation

3. **Dashboard** (`/dashboard`)
   - Left sidebar: Module list with progress indicators
   - Main area: Current challenge or module selector
   - Progress bar: Overall completion %
   - Each module shows: X/Y challenges completed

4. **Challenge Page** (`/challenge/{m}/{c}`)
   - Top: Challenge title + learning objective
   - Left/Top panel: Lesson markdown (rendered)
   - Right/Bottom panel: Code editor (Monaco Editor recommended)
   - Submit button
   - Evaluation feedback area (appears after submit)
   - Remediation hints (if failed)
   - Next button (if passed)

### State Management

**Global State:**
- `user`: Current user profile
- `learningPath`: Full learning path
- `currentChallenge`: {module, challenge, status}
- `progress`: Progress summary

**Challenge State:**
- `lessonMarkdown`: Rendered lesson
- `codingChallenge`: Challenge prompt + starter code
- `userCode`: Code in editor
- `evaluation`: Latest evaluation result
- `remediation`: Hints (if failed)
- `attemptCount`: Current attempt number

### Key UI Components

**ModuleCard**: Shows module with progress ring/bar
**ChallengeItem**: Individual challenge with status icon (locked/in-progress/completed)
**MarkdownViewer**: Renders lesson markdown with syntax highlighting
**CodeEditor**: Monaco Editor with starter code
**EvaluationPanel**: Shows pass/fail, score, feedback, hints
**ProgressBar**: Visual progress tracker

---

## Running the System

### Start Server
```bash
python3 app.py
# Runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Test API
```bash
# Simple test (avoids rate limits)
python3 test_api_simple.py

# Full test (wait 5+ minutes between runs)
python3 test_api.py
```

### Environment Variables
```bash
# .env file required
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### Rate Limits (Gemini Free Tier)
- ~60 requests/minute
- System handles automatically with:
  - 10s initial delay before batch generation
  - 10s between module generations
  - Exponential backoff (15s → 30s → 45s) on 429 errors
  - Up to 3 retries per call

---

## Error Handling

**All endpoints return:**
```json
{
  "detail": "Error message with full traceback"
}
```

**Common Errors:**
- `400` - Invalid input (wrong experience level, etc.)
- `404` - Resource not found (user, module, challenge)
- `500` - Server error (agent failure, database error)

**Rate Limit Handling**: Automatic retry with exponential backoff

---

## Frontend Integration Example

```javascript
// 1. Setup
const setupResponse = await fetch('http://localhost:8000/setup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    learning_goal: "Build REST APIs",
    experience_level: "Beginner"
  })
});
const { learning_path } = await setupResponse.json();

// 2. Approve Path
await fetch('http://localhost:8000/path/approve', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ learning_path })
});

// 3. Get Challenge
const challenge = await fetch('http://localhost:8000/challenge/1/1')
  .then(r => r.json());

// Display challenge.lesson_markdown (render as HTML)
// Load challenge.coding_challenge.starter_code into editor

// 4. Submit Code
const result = await fetch('http://localhost:8000/challenge/1/1/submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code: userCodeFromEditor })
}).then(r => r.json());

// Show result.evaluation feedback
// If failed, show result.remediation hints
// If passed, unlock next challenge

// 5. Track Progress
const progress = await fetch('http://localhost:8000/progress')
  .then(r => r.json());
// Display progress.completion_percentage
// Show progress.modules for dashboard

// 6. Get Challenge Titles for Dashboard
const metadata = await fetch('http://localhost:8000/challenges/metadata')
  .then(r => r.json());
// Display challenge titles alongside progress indicators
```

---

## Key Implementation Notes

1. **Caching**: Lessons and challenges cached in database after first generation - subsequent loads are instant

2. **Open Access**: All challenges are accessible from the start - learn at your own pace

3. **Stateful Workflow**: LangGraph maintains full session state across requests via checkpointing

4. **No Code Execution**: Evaluation is LLM-based reasoning, not actual code execution (security)

5. **Adaptive Teaching**: All content personalized to user's experience level

6. **Retry Logic**: Both agents have 3-retry logic for JSON errors and rate limits

7. **Single User MVP**: Database supports multi-user but API assumes single user (`get_first_user_profile()`)

---

## Future Enhancements (Not Yet Implemented)

- Interviewer Agent (end-of-module Q&A)
- Multi-user authentication
- Real code execution sandbox
- Solution reveal after max attempts
- Learning analytics dashboard
- Export progress reports

---

**Last Updated**: 2025-11-08
**Backend Status**: ✅ Production Ready
**Frontend Status**: ⬜ Not Started
