# PRP: VideoFlipper

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | VideoFlipper |
| **Type** | SaaS |
| **Version** | 1.0 |
| **Created** | 2026-08-29 |
| **Complexity** | Medium |

---

## PRODUCT OVERVIEW

**Description:** VideoFlipper lets content creators submit a YouTube video URL and flip it horizontally, vertically, or both — the backend downloads the source video, processes the flip, and produces a ready-to-download output optimized for reposting across social platforms.

**Value Proposition:** Content creators repost clips across platforms constantly and get flagged for duplicate content; a one-click flip (no file wrangling — just paste a link) makes reposting fast and avoids that friction.

**MVP Scope:**
- [ ] User registration and login (email/password)
- [ ] Submit a YouTube URL and select flip direction (horizontal/vertical/both)
- [ ] Backend downloads the source video and processes the flip, showing live status
- [ ] Download the flipped output
- [ ] View history of past flips (filter/search, re-download, delete)
- [ ] Dashboard with basic usage stats

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy | skills/DATABASE.md |
| Auth | JWT + bcrypt (email/password only, no OAuth) | skills/BACKEND.md |
| UI | Tailwind + shadcn/ui | skills/FRONTEND.md |
| Video Processing | yt-dlp (download) + ffmpeg (flip) | skills/BACKEND.md |
| Testing | pytest + RTL | skills/TESTING.md |
| Deployment | Docker + GitHub Actions | skills/DEPLOYMENT.md |

---

## DATABASE MODELS

### User Model
- id, email, hashed_password, full_name, is_active, is_verified, created_at

### RefreshToken Model
- id, user_id (FK → User), token, expires_at, revoked

### Video Model
- id, user_id (FK → User)
- youtube_url: str
- youtube_video_id: str
- source_title: str | null
- storage_url: str | null (downloaded source, before flipping)
- flip_direction: enum(horizontal, vertical, both)
- status: enum(pending, downloading, processing, completed, failed)
- output_url: str | null
- duration_seconds: float | null
- file_size_bytes: int | null
- error_message: str | null
- created_at, updated_at

---

## MODULES

### Module 1: Authentication
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Get tokens |
| POST | /auth/refresh | Refresh access token |
| POST | /auth/logout | Revoke refresh token |
| GET | /auth/me | Current user profile |
| PUT | /auth/me | Update profile |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /login | LoginPage | LoginForm |
| /register | RegisterPage | RegisterForm |
| /forgot-password | ForgotPasswordPage | ForgotPasswordForm |
| /profile | ProfilePage (protected) | ProfileForm |

---

### Module 2: Videos
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/videos | Submit a YouTube URL + flip direction (creates job) |
| GET | /api/videos | List current user's videos (supports `status`, `search` filters — powers History) |
| GET | /api/videos/{id} | Get video detail/status |
| GET | /api/videos/{id}/download | Download the flipped output |
| DELETE | /api/videos/{id} | Delete a video and its stored files |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /videos/new | VideoSubmitPage | YoutubeUrlForm, FlipDirectionSelect |
| /videos | VideoListPage | VideoCard, StatusBadge |
| /videos/{id} | VideoDetailPage | StatusBadge, DownloadButton |

**Backend Notes:**
- `POST /api/videos` validates the URL synchronously (format + resolvable + public), then enqueues a background job and returns `status=pending` immediately.
- Background job: download via yt-dlp (`status=downloading`) → flip via ffmpeg (`status=processing`) → upload output to storage (`status=completed`) or set `status=failed` with `error_message`.
- Enforce max source duration/size limits before downloading.

---

### Module 3: Projects/History
**Agents:** FRONTEND-AGENT (reuses Videos backend — no new endpoints or models)

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/videos?status=completed&search=... | Filtered/searchable history (same endpoint as Videos list) |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /history | HistoryPage | VideoCard, FilterBar, SearchInput |

---

### Module 4: Dashboard
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/dashboard/stats | Total videos flipped, storage used, recent activity |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /dashboard | DashboardPage | StatCard, RecentActivityList |
| /settings | SettingsPage | SettingsForm |

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: User, RefreshToken, Video models + migrations, database.py
- BACKEND-AGENT: main.py, config.py, project structure, storage + yt-dlp/ffmpeg service scaffolding
- FRONTEND-AGENT: Vite setup, folder structure, base components (StatusBadge, FlipDirectionSelect)
- DEVOPS-AGENT: Docker (incl. ffmpeg in image), CI/CD, env files

**Validation Gate 1:** `pip install`, `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend parallel per module)**
- Auth Module: JWT endpoints + Login/Register/Profile pages
- Videos Module: submit/list/detail/download/delete endpoints + background job (download → flip → upload) + Submit/List/Detail pages
- Projects/History Module: History page consuming the Videos list endpoint
- Dashboard Module: stats endpoint + Dashboard/Settings pages

**Validation Gate 2:** `ruff check`, `mypy`, `npm run lint`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (incl. mocked yt-dlp/ffmpeg calls) + RTL tests, 80%+ coverage
- REVIEW-AGENT: Security audit (YouTube URL validation/SSRF, JWT handling), performance review
- RESEARCH-AGENT: Validate yt-dlp/ffmpeg best practices, YouTube ToS considerations

**Final Validation:** Full test suite, docker build, health checks

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=postgresql://user:password@localhost:5432/videoflipper
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
STORAGE_BUCKET=videoflipper-storage
STORAGE_ACCESS_KEY=your-access-key
STORAGE_SECRET_KEY=your-secret-key
VITE_API_URL=http://localhost:8000
```

---

## RISKS / OPEN QUESTIONS

- **YouTube ToS:** Downloading YouTube content server-side must respect YouTube's Terms of Service — confirm the intended use case (user-owned/licensed content) before shipping.
- **No OAuth:** Auth is email/password only per product decision — no Google login.
- **No payments:** Not needed for MVP; revisit if usage-based limits are required later.

---

## NEXT STEP

Execute with parallel agents:
`/execute-prp PRPs/videoflipper-prp.md`
