# New Peak

New Peak (Peak Practice) is a study platform for the PAES, Chile's university admission exam
(Prueba de Acceso a la Educación Superior). It replaces an older legacy application and combines
exam practice, study-progress tracking, a weekly routine planner, and AI-assisted study features
in a single self-hostable web application.

GitHub repository: [Hunther4/New-Peak](https://github.com/Hunther4/New-Peak)

## Features

- **Exam practice** — PAES-style question banks organized by subject, competency, eje temático,
  topic, and subtopic.
- **Study progress tracking** — mastery maps, retention metrics, and spaced-repetition state
  driven by FSRS parametric tabs (per-subtopic learning states, Leitner boxes, next-review dates).
- **Weekly study routine planner** — recurring weekly study routines with per-day sessions.
- **AI-assisted study** — an AI study coach plus adaptive modules: mental math, math thinking,
  memory training, IQ practice, and cognitive skill sessions.
- **Admission tooling** — admission-score computation against PAES scaling curves.
- **Hardened web surface** — security headers with per-request CSP nonces, upload MIME
  whitelisting, and rate limiting.

## Tech Stack

**Backend** (Python 3.11)

- FastAPI + Uvicorn, SQLModel + SQLite (single-file database), Pydantic v2.
- AI providers: OpenAI and Groq APIs; ChromaDB for lightweight RAG.
- `cryptography` (ECDSA verification, AES-256-GCM), bcrypt, slowapi rate limiting.
- Tests: pytest + pytest-cov (coverage `fail_under = 72`); lint: ruff (pinned).

**Frontend**

- React 19, React Router 7, Zustand for state, Tailwind CSS 4, Vite build tooling.
- Tests: Vitest 4 + Testing Library + jsdom; coverage via `@vitest/coverage-v8`.
- Package manager: pnpm.

**CI** (GitHub Actions, `.github/workflows/ci.yml`) — Python 3.11 + Node 22 jobs:
ruff check, pytest with coverage, vitest with coverage thresholds
(statements 38 / branches 28 / functions 32 / lines 39), and a production `vite build`.

## Getting Started

Prerequisites:

- Windows with PowerShell 5.1+
- Python 3.11+ (a backend virtualenv at `backend/venv` with dependencies installed from
  `backend/requirements.txt`)
- Node 22 + [pnpm](https://pnpm.io/) (frontend dependencies installed in `frontend/`)

Launch both services with the Windows launcher:

```powershell
.\paes.ps1
```

The launcher:

1. Verifies the backend directory, frontend directory, and `backend/venv` python exist.
2. Inspects the configured ports — a port held by a foreign process aborts the run instead of
   leaving a half-launched stack.
3. Starts the FastAPI backend with uvicorn (`--reload`) and the Vite dev server
   (`--strictPort`), reusing either service if it already answers on its port.
4. Polls both services until they actually answer HTTP, then opens the browser.
5. Appends service output to `logs/backend.log` and `logs/frontend.log`.

Optional parameters: `-BackendPort` (default 8000), `-FrontendPort` (default 7700),
`-ReadyTimeoutSeconds` (default 90), `-NoBrowser`.

Dev URLs:

- Backend: http://127.0.0.1:8000/ (interactive OpenAPI docs under `/docs`)
- Frontend: http://127.0.0.1:7700/ (Vite proxies `/api` and `/uploads` to the backend)

Environment configuration is documented in `backend/.env.example`. Never commit real
`backend/.env` values or API keys.

## Running Tests and Quality Gates

Backend (from `backend/`, using the venv interpreter):

```bash
python -m pytest --cov=api --cov=core --cov=models --cov=services --cov-report=term-missing
ruff check .
```

- Coverage is enforced at 72% via `backend/pyproject.toml` (`fail_under = 72`), across the
  `api`, `core`, `models`, and `services` packages.
- Ruff is pinned (`ruff==0.8.6`, target Python 3.11) and CI requires zero lint errors.

Frontend (from `frontend/`):

```bash
pnpm install --frozen-lockfile
pnpm run test:coverage
pnpm build
```

- Vitest runs in a jsdom environment; v8 coverage fails below the thresholds configured in
  `frontend/vite.config.js` (statements 38, branches 28, functions 32, lines 39).
- `pnpm lint` runs ESLint (currently not CI-enforced).

## Project Status

- A hardened baseline is complete: security headers, CSP nonces, upload MIME checks, rate
  limiting, and passing CI quality gates.
- A multi-user foundation program ([openspec/changes/multi-user-foundation](openspec/changes/multi-user-foundation/proposal.md))
  is in progress. Slice S1 (identity schema + ECDSA crypto primitives) has landed on
  `feature/multi-user-foundation/*` branches; slices S2–S11 are pending.
- Today the app still has a single shared API key; all user data is shared global state until
  the ownership slices land.

### Multi-user roadmap (11 chained slices)

| Slice | Theme | Status |
|---|---|---|
| S1 | Identity schema (`users`, `user_devices`, `auth_challenges`, `auth_sessions`) + ECDSA crypto primitives | Landed |
| S2 | Enrollment + one-shot legacy-key bootstrap | Pending |
| S3 | Challenge/verify round + bearer session lifecycle | Pending |
| S4 | Scope every PAES query to the principal (remove client-supplied `user_id`) | Pending |
| S5 | Browser device-key client, auth slice, enrollment screen | Pending |
| S6 | Login screen + auth gate | Pending |
| S7 | Destructive per-user ownership migration (014) | Pending |
| S8 | Scope the whole Peak Practice track to the principal | Pending |
| S9 | Per-user encrypted provider keys (AES-256-GCM, HKDF subkeys) | Pending |
| S10 | Per-principal credential resolution; legacy-key migration; OpenAI routing | Pending |
| S11 | Make the identity boundary the default in the test suite | Pending |

## Repository Layout

```
backend/    FastAPI application: api routes, core services, models, migrations, tests
frontend/   React + Vite client: components, store slices, tests
openspec/   Spec-driven change proposals for the multi-user foundation program
docs/       Project documentation
books/      Study material assets
data/       Local data assets
.github/    CI workflows
paes.ps1    Windows launcher (backend + frontend + browser)
```

## Branch Model

- `main` — stable, protected by CI.
- `feature/multi-user-foundation` — tracker branch holding the multi-user program.
- Each slice lands as a feature-slice PR chained off the tracker branch (S1 → S2 → … → S11),
  and the completed program merges back into `main` once.
