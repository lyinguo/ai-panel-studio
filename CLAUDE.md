# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

AI Panel Studio is a full-stack app for running AI-powered roundtable discussions. Users enter a topic and the system generates multiple AI experts with distinct stances who debate in real-time via SSE streaming.

### Data Flow (Critical Path)

```
User Input → POST /api/discussions → LlmService generates participants → DB persist
                                         ↓ (async background task)
DiscussionEngine.run_discussion()
    ├── select_next_speaker()    ← speaker fairness algorithm
    ├── stream_chat(messages)    ← calls DeepSeek API, strips <think> tags
    ├── EventBus.publish()       ← per-discussion async queue
    └── consensus extraction     ← periodic LLM call
                                         ↓
SSE endpoint → EventSource (browser) → Zustand store → React UI
```

### Backend Structure

```
backend/
├── app/main.py              ← FastAPI entry, CORS (hardcoded localhost:5173), tables auto-created on startup
├── app/models.py            ← 4 SQLAlchemy models (see below)
├── app/api/discussions.py   ← 5 REST endpoints + SSE + background task
│                              SSE: EventSourceResponse(event_generator) wrapping EventBus.event_stream()
│                              Background: asyncio.create_task() fires DiscussionEngine after HTTP response
├── app/services/
│   ├── llm_service.py       ← DeepSeek API calls,  thinking tag stripper, fallback data
│   │                          Key methods: generate_participants, stream_chat, _call_llm_sync (consensus)
│   │                          API path auto-probed (cached via _resolve_api_path), fallback on any failure
│   ├── discussion_engine.py ← Speaker scheduling, prompt assembly, run_discussion flow
│   │                          Key methods: select_next_speaker, build_system_prompt, run_discussion
│   └── event_bus.py         ← Per-discussion asyncio.Queue, SSE generator
│                              Methods: publish, subscribe, unsubscribe, event_stream (async generator)
├── app/core/config.py       ← pydantic-settings, auto-finds .env (searches 3 paths)
├── app/db/__init__.py       ← SQLAlchemy engine + session factory + get_db() dependency
└── tests/                   ← 20 pytest tests, TDD-style
```

### Frontend Structure

```
frontend/src/
├── pages/Studio.jsx         ← Main page: Guest bar + Transcript + Floating consensus + Footer
│                              States: idle (input bar) → in_progress (status dot) → completed (summary + reset)
├── components/              ← 5 UI components, each self-contained (custom CSS, no framework)
│   ├── GuestCard/GuestPanel ← Circular avatars with status glow (border-left color per speaker)
│   ├── Transcript           ← Full-width chat area with auto-scroll
│   ├── MessageBubble        ← Color-accented speech bubbles
│   └── ConsensusPanel       ← Floating overlay (bottom-right fixed)
├── stores/studioStore.js    ← Zustand: SSE-driven state with chunk buffering
│                              Transitions: discussionStatus (idle→starting→in_progress→completed)
│                              _pendingContent accumulates chunks between punctuation flushes
└── hooks/useDiscussion.js   ← EventSource connection + event dispatch
                               Auto-reconnect via browser EventSource built-in retry
                               Cleanup on unmount via useEffect
```

### Database (SQLite)

4 tables, all keyed by `discussion_id` (the isolation boundary):

| Table | Key Relationship | Notes |
|---|---|---|
| `discussions` | PK | topic, status, expert_count |
| `participants` | FK → discussions | role(host/expert), name, title, stance, color_code |
| `messages` | FK → discussions + participants | content, ORDER BY id ASC |
| `consensus` | FK → discussions (UNIQUE) | 1:1, agreements/divergences as JSON arrays |

**Critical rule**: Every query MUST filter by `discussion_id`. No cross-discussion reads.

## Commands

### Environment

```bash
# Backend (conda)
conda activate ai-panel-studio
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Running

```bash
# One-click (double-click start.bat or)
start.bat

# Manual - Terminal 1 (backend)
conda activate ai-panel-studio
cd backend
uvicorn app.main:app --reload --port 8000

# Manual - Terminal 2 (frontend)
cd frontend
npm run dev
```

### Tests

```bash
# All backend tests
conda activate ai-panel-studio
cd backend
pytest tests/ -v

# Single test file
pytest tests/test_sse_isolation.py -v

# Single test
pytest tests/test_llm_service.py::TestParticipantStructure::test_should_contain_exactly_one_host -v

# E2E tests (servers must be running)
cd e2e
npx playwright test
```

## Key Design Constraints

1. **Discussion isolation** — Every feature must assume multiple simultaneous discussions. No global mutable state. All DB queries require `discussion_id` filter.
2. **No round-robin** — Speaker selection must feel organic, not A→B→C. Uses fairness algorithm: unspoken experts first → least-spoken first with 10% chance of same-speaker continuation (simulates interruption).
3. **1-2 sentence limit** — System prompt enforces this. Discussion engine prompts repeat it in every round variant (early rounds, middle rounds, final rounds each get different prompt phrasing).
4. **<think> tag stripping** — `ThinkTagStripper` is a **character-level state machine** (not regex) that handles partial tag boundaries across streaming chunks. It maintains `_in_think` boolean state and buffers incomplete tag fragments. Both `stream_chat` and `_call_llm` / `_call_llm_sync` routes through it.
5. **SSE 3-event contract** — `guest_status_change` (thinking/speaking/idle), `message_chunk` (streaming with is_final flag), `consensus_update`. Frontend only consumes these plus `discussion_status` (in_progress/completed).
6. **No API key? Fallback works** — `llm_service.py` generates contextually relevant content via `_fallback_any()` which detects the prompt type (consensus extraction, participant generation, or speech) and returns appropriate mock data. `_generate_speech()` parses the prompt to extract name, stance, and topic for realistic 1-2 sentence replies.
7. **Chunk buffering** — Frontend `studioStore.updateTypingContent` buffers partial SSE chunks and flushes on punctuation ( `。.!?！？\n`) or when accumulated length exceeds 30 characters. `finalizeTyping` appends remaining buffer before committing to message history.

## Discussion Round Scheduling

- Total rounds = `min(max_rounds, len(experts) * 2 + 3)`
- Round progression: host opens → round 1-N (early: core insight → mid: debate/collision → final: closing statements)
- Consensus extraction every 3 rounds and on final round
- Final consensus + host summary after the round loop ends
- `discussionStatus` transitions: `pending` → `in_progress` → `completed`

## MCP Tools Available

This project has a SQLite MCP server configured (`.claude/settings.local.json`). Use it to inspect the real database:
- `query "SELECT * FROM discussions ORDER BY id DESC LIMIT 1"` — never guess table schemas
- `query "PRAGMA table_info(participants)"` — check column types
- `query "SELECT COUNT(*) FROM messages WHERE discussion_id=?"` — verify data

## Testing Patterns

- All backend tests use `unittest.mock.patch.object` to mock service methods — no real API calls
- `conftest.py` provides `AsyncMock` for Python 3.7+ compatibility
- SSE isolation tests create separate `asyncio.Queue` instances per discussion
- Discussion engine tests verify non-determinism: run 20+ iterations, assert not purely sequential
- E2E tests rely on specific CSS class names: `.guest-card`, `.guest-card__indicator`, `.msg-bubble`, `.msg-bubble__name`, `.consensus__item`, `.transcript`, `.transcript__empty`, `.transcript__ending`

## Common Gotchas

- **The API path is auto-probed and cached** — `_resolve_api_path()` probes both `/v1/chat/completions` and `/chat/completions` on first call, then caches in a class variable. If you change `DEEPSEEK_API_BASE_URL` at runtime, restart the server.
- **Message `is_final` marks DB persistence** — When SSE `message_chunk` arrives with `is_final: true`, the message has been persisted to SQLite. The `message_id` field in `is_final` is the database primary key. Frontend uses this to finalize the typing cursor.
- **No CSS framework** — The frontend uses plain CSS (imported in `main.jsx`). No Tailwind, no CSS-in-JS. Styling is class-based with BEM-like naming.
- **The `_pendingContent` buffer lives in Zustand** — It's not React state, so reading it requires `get()` not `state`. The buffer survives re-renders but resets on `resetDiscussion()`.
- **`discussionStatus` drives layout** — The main Studio.jsx footer renders differently for each status: `idle` shows input bar, `in_progress` shows status dot, `completed` shows summary.
