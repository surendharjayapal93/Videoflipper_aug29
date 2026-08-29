# INITIAL.md - VideoFlipper Product Definition

> Flips videos vertically/horizontally for social media, for content creators.

---

## PRODUCT

### Name
VideoFlipper

### Description
VideoFlipper lets content creators upload a video and flip it horizontally, vertically, or both — producing a ready-to-download output optimized for reposting across social platforms.

### Target User
Content creators who need to quickly reformat/mirror video clips for social media.

### Type
- [x] SaaS (Software as a Service)

---

## TECH STACK

### Backend
- [x] FastAPI + Python

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL

### Authentication
- [x] Email/Password only

### UI Framework
- [x] Tailwind + shadcn/ui

### Payments
- [ ] None (not needed for MVP)

---

## MODULES

### Module 1: Authentication (Required)

**Description:** User authentication and authorization

**Models:**
- User: id, email, hashed_password, full_name, is_active, is_verified, created_at
- RefreshToken: id, user_id, token, expires_at, revoked

**API Endpoints:**
- POST /auth/register - Create new account
- POST /auth/login - Login with email/password
- POST /auth/refresh - Refresh access token
- POST /auth/logout - Revoke refresh token
- GET /auth/me - Get current user profile
- PUT /auth/me - Update profile

**Frontend Pages:**
- /login - Login page
- /register - Registration page
- /forgot-password - Forgot password page
- /profile - User profile page (protected)

---

### Module 2: Videos

**Description:** Submit a YouTube video URL, choose a flip direction, process it, and download the result. Direct file upload is not supported — the backend downloads the source video from YouTube.

**Models:**
```
Video:
  - id, user_id (FK)
  - youtube_url: str
  - youtube_video_id: str
  - source_title: str | null
  - storage_url: str | null       # downloaded source, before flipping
  - flip_direction: enum(horizontal, vertical, both)
  - status: enum(pending, downloading, processing, completed, failed)
  - output_url: str | null
  - duration_seconds: float | null
  - file_size_bytes: int | null
  - error_message: str | null
  - created_at, updated_at
```

**API Endpoints:**
```
POST   /api/videos              - Submit a YouTube URL + flip direction (creates job)
GET    /api/videos              - List current user's videos
GET    /api/videos/{id}         - Get video detail/status
GET    /api/videos/{id}/download - Download the flipped output
DELETE /api/videos/{id}         - Delete a video and its files
```

**Frontend Pages:**
- /videos/new - Submit page (paste YouTube URL + select flip direction)
- /videos - Video list (status badges: pending/downloading/processing/completed/failed)
- /videos/{id} - Video detail/status page with download button

---

### Module 3: Projects/History

**Description:** Historical view over past flips — reuses the Video model, no new entity.

**API Endpoints:**
```
GET /api/videos?status=completed&search=...  - Filtered/searchable history (reuses Videos endpoints)
```

**Frontend Pages:**
- /history - Filterable/searchable list of past videos with re-download and delete actions

---

### Module 4: Dashboard

**Description:** Overview and usage stats, aggregated from Video data (no new entity).

**API Endpoints:**
```
GET /api/dashboard/stats - Total videos flipped, storage used, recent activity
```

**Frontend Pages:**
- /dashboard - Main dashboard with widgets and stats
- /settings - User settings and preferences

---

## MVP SCOPE

### Must Have (MVP)
- [x] User registration and login (email/password)
- [x] Submit a YouTube URL and select flip direction (horizontal/vertical/both)
- [x] Backend downloads the source video and processes the flip, showing status (pending/downloading/processing/completed/failed)
- [x] Download the flipped output
- [x] View history of past flips (filter/search, re-download, delete)
- [x] Dashboard with basic usage stats

### Nice to Have (Post-MVP)
- [ ] Email notifications when processing completes
- [ ] Analytics dashboard (deeper usage metrics/charts)
- [ ] Admin panel
- [ ] Payments/subscriptions

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] JWT tokens work correctly with refresh
- [ ] Protected routes redirect to login

### Videos
- [ ] User can submit a YouTube URL and select a flip direction
- [ ] Backend validates the URL, downloads the source video, and processes the flip (horizontal/vertical/both), storing the output
- [ ] User can see live status of processing (pending → downloading → processing → completed/failed)
- [ ] User can download the completed flipped video
- [ ] User can delete a video (removes DB record + stored files)

### Projects/History
- [ ] User can view a filterable/searchable list of past videos
- [ ] User can re-download or delete from history

### Dashboard
- [ ] User sees total videos flipped, storage used, and recent activity

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully

---

## SPECIAL REQUIREMENTS

### Security
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints
- [x] SQL injection prevention
- [x] XSS prevention
- [x] YouTube URL validation (must resolve to a valid, public, downloadable video; enforce max duration/size limits)

### Integrations
- [x] YouTube downloader (e.g. yt-dlp) to fetch source video server-side
- [x] Storage service (for downloaded source + flipped output files)
- [ ] Email service for notifications (post-MVP)
- [ ] Stripe/payments (post-MVP)

> **Note:** Downloading YouTube content is subject to YouTube's Terms of Service. Confirm the intended use case (e.g., user-owned/licensed content) complies before shipping.

---

## AGENTS

> These 6 agents will build your product in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | All database models |
| BACKEND-AGENT | Builds API endpoints and services | All modules' backends |
| FRONTEND-AGENT | Creates UI pages and components | All modules' frontends |
| DEVOPS-AGENT | Sets up Docker, CI/CD, environments | Infrastructure |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/videoflipper-prp.md
```
