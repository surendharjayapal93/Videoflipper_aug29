# CLAUDE.md - VideoFlipper Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** VideoFlipper
**Description:** Flips videos vertically/horizontally for social media, for content creators.
**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + Vite + TypeScript
- Database: PostgreSQL + SQLAlchemy
- Auth: Email/Password only (JWT)
- UI: Tailwind + shadcn/ui

---

## Project Structure

```
videoflipper/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── refresh_token.py
│   │   │   └── video.py
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── videos.py
│   │   │   └── dashboard.py
│   │   ├── services/
│   │   │   ├── youtube_downloader.py
│   │   │   ├── video_processing.py
│   │   │   └── storage.py
│   │   └── auth/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── Login.tsx, Register.tsx, Profile.tsx
│   │   │   ├── VideoSubmit.tsx, VideoList.tsx, VideoDetail.tsx
│   │   │   ├── History.tsx
│   │   │   └── Dashboard.tsx, Settings.tsx
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── context/
│   │   └── types/
│   └── package.json
├── .claude/
│   └── commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints
def get_video(db: Session, video_id: int) -> Video:
    pass

# ALWAYS add docstrings for public functions
def create_video(db: Session, data: VideoCreate) -> Video:
    """
    Create a new video processing job from a YouTube URL.

    Args:
        db: Database session
        data: Video creation data (YouTube URL + flip direction)

    Returns:
        Created Video object with status=pending
    """
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data
interface VideoProps {
  id: number;
  youtubeUrl: string;
  sourceTitle: string | null;
  flipDirection: "horizontal" | "vertical" | "both";
  status: "pending" | "downloading" | "processing" | "completed" | "failed";
  outputUrl: string | null;
}

// NO any types allowed
const fetchVideo = async (id: number): Promise<VideoProps> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- ❌ Never use `print()` - use `logging` module
- ❌ Never store passwords in plain text
- ❌ Never hardcode secrets - use environment variables
- ❌ Never use `SELECT *` - specify columns
- ❌ Never skip input validation
- ❌ Never pass a raw YouTube URL to the downloader without validating it resolves to a public, downloadable video and enforcing duration/size limits

### Frontend
- ❌ Never use `any` type
- ❌ Never leave console.log in production
- ❌ Never skip error handling in async operations
- ❌ Never use inline styles - use Tailwind

---

## Module-Specific Rules

### Videos Module
- Every Video must belong to a user (`user_id` foreign key)
- `status` must be one of: `pending`, `downloading`, `processing`, `completed`, `failed`
- `flip_direction` must be one of: `horizontal`, `vertical`, `both`
- Direct file upload is not supported — input is a YouTube URL only
- Validate the YouTube URL before accepting the job (valid format, public/downloadable, within duration/size limits)
- Deleting a Video must also delete its stored files (downloaded source + output)
- Downloading and processing run as background jobs — the submit endpoint returns immediately with `status=pending`
- Respect YouTube's Terms of Service — this feature assumes user-owned/licensed content

### Projects/History Module
- Reuses the Video model; do not create a separate History entity
- History queries must be scoped to the requesting user

### Dashboard Module
- Stats are computed from Video records, not stored separately

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/videos`
- Return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 401: Unauthorized
  - 404: Not Found
  - 409: Conflict

---

## Authentication

Email/Password only (no OAuth for MVP).

### JWT Configuration
- Access token expires: 30 minutes
- Refresh token expires: 7 days
- Algorithm: HS256

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/videoflipper

# Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Storage (raw + flipped video files)
STORAGE_BUCKET=videoflipper-storage
STORAGE_ACCESS_KEY=your-access-key
STORAGE_SECRET_KEY=your-secret-key

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → Backend models
- BACKEND-AGENT → API development
- FRONTEND-AGENT → UI components
- TEST-AGENT → Testing
- REVIEW-AGENT → Code review
- DEVOPS-AGENT → Deployment

Read agent definitions in `/agents/` folder.
