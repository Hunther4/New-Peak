<div align="center">

# New Peak

**High-Performance PAES Preparation Platform**  
*3PL Item Response Theory Calibration · FSRS Spaced Repetition · Hardened Deliberate Practice*

[![CI](https://github.com/Hunther4/New-Peak/actions/workflows/ci.yml/badge.svg)](https://github.com/Hunther4/New-Peak/actions/workflows/ci.yml)
![Backend Coverage](https://img.shields.io/badge/backend%20coverage-%E2%89%A572%25-brightgreen?style=flat-square&logo=pytest&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-4-38B2AC?style=flat-square&logo=tailwindcss&logoColor=white)
![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-261230?style=flat-square&logo=ruff&logoColor=white)
![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square)

</div>

---

## Overview

**New Peak** is a modern, self-hostable preparation and psychometric tracking system engineered specifically for the **PAES** (Prueba de Acceso a la Educación Superior, Chile's university admission exam). 

Built to replace legacy study software, New Peak bridges the gap between raw question drills and cognitive mastery through:
1. **Psychometric Precision:** Official DEMRE curve scaling and 3-Parameter Logistic (3PL) Item Response Theory ($\theta$ latent ability estimation via Bayes EAP and Newton-Raphson MLE).
2. **Memory Retention:** FSRS (Free Spaced Repetition Scheduler) with adaptive Leitner progression isolated per subtopic.
3. **Targeted Review:** *Cuaderno Negro de Errores* (Error Vault) with zero-forgiveness revenge study modes.
4. **Hardened Multi-User Foundation:** Nonced CSP security, ECDSA device signatures, and spec-driven multi-user partitioning.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend (React 19 + Vite)"]
        UI["Tailwind CSS 4 UI Components"]
        Zustand["Zustand Store Slices (PAES, Gym, Settings)"]
        WebCrypto["WebCrypto Primitives (ECDSA P-256)"]
        RoutineBar["Customizable Weekly Routine Bar"]
    end

    subgraph Gateway["API Gateway & Middleware (FastAPI)"]
        CSP["Per-Request CSP Nonce & Security Headers"]
        Limiter["SlowAPI Rate Limiter"]
        AuthMdl["Identity & Principal Resolver (Bearer/ECDSA)"]
    end

    subgraph CoreServices["Domain Engine & Services"]
        IRT["3PL IRT Ability Estimator (Bayes EAP / MLE)"]
        FSRS["FSRS Scheduler & Spaced Repetition Engine"]
        Coach["Socratic AI Coach (ChromaDB RAG + DEMRE Docs)"]
        Curriculum["PAES Curriculum & Question Bank (1,100+ items)"]
    end

    subgraph DataStore["Persistence & AI Providers"]
        SQLite[("SQLite (peak.db)\nIdempotent Migrations")]
        Chroma[("ChromaDB Vector Store")]
        LLM["AI Providers (OpenAI / Groq / Local LM Studio)"]
    end

    UI --> Zustand
    Zustand --> WebCrypto
    Zustand -->|REST API + JSON| Gateway
    Gateway --> CSP --> Limiter --> AuthMdl
    AuthMdl --> CoreServices
    CoreServices --> SQLite
    Coach --> Chroma
    Coach --> LLM
```

---

## Key Features

* **3PL Item Response Theory (IRT):** Calculates student ability ($\theta$) across discrimination ($a$), difficulty ($b$), and guessing ($c$) parameters calibrated from official DEMRE scaling tables.
* **FSRS Spaced Repetition:** Calculates retrievability and optimal review intervals per subject subtopic (`Matemática M1/M2`, `Lectura`, `Ciencias`).
* **Weekly Study Routine Planner:** 1-Click scheduling toolbar with persistent custom presets (e.g., *Enfoque M1 UBB*, *Full Matemáticas*), collapsible compact views, and automated day tracking.
* **Error Vault & Revenge Mode:** Dedicated catalog of missed questions tagged by misconception type with step-by-step distractor resolutions.
* **Cognitive Gym:** Integrated mental math, Dual N-Back working memory training, and cognitive bridges for academic endurance.
* **Hardened Perimeter:** Dynamic Content Security Policy (CSP) nonces per request, strict MIME-type sniffing prevention for uploads, bcrypt 72-byte password guards, and ECDSA signature verifications.

---

## Quickstart

### Prerequisites
* **Windows** with PowerShell 5.1+
* **Python 3.11+** (virtual environment inside `backend/venv`)
* **Node.js 22+** and [pnpm](https://pnpm.io/)

### 1-Click Launch
Start both the FastAPI backend and Vite frontend concurrently using the automated PowerShell launcher:

```powershell
.\paes.ps1
```

The launcher automatically:
1. Validates virtual environments and dependencies.
2. Checks port availability (`8000` and `7700`) to prevent port conflicts or zombie processes.
3. Boots FastAPI (`--reload`) and Vite (`--strictPort`).
4. Polls HTTP endpoints until live readiness is confirmed, then launches your default browser.

**Default URLs:**
* Frontend Web App: [http://localhost:7700](http://localhost:7700)
* Backend OpenAPI Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Configuration

Environment variables are loaded from `backend/.env`. A documented template is available at [`backend/.env.example`](backend/.env.example).

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLite connection string | `sqlite:///./peak.db` |
| `OPENAI_API_KEY` | Optional OpenAI key for Socratic Coach | `""` |
| `GROQ_API_KEY` | Optional Groq key for fast inference | `""` |
| `LM_STUDIO_URL` | Local LLM inference server endpoint | `http://127.0.0.1:1234/v1` |
| `PEAK_ENROLLMENT_TOKEN` | Secret token required to register new devices (when enabled) | `""` |
| `DISABLE_AUTH` | Local dev auth bypass (strictly rejected when `PRODUCTION=1`) | `0` |

---

## Quality Gates & Testing

Quality standards are strictly enforced locally and on GitHub Actions CI.

### Backend (Pytest + Ruff)
Executed with the virtual environment interpreter from `backend/`:

```bash
# Run 817+ unit & integration tests with mandatory 72% coverage threshold
python -m pytest --cov=api --cov=core --cov=models --cov=services --cov-report=term-missing

# Lint with zero-tolerance ruff rule checks
ruff check .
```

* Coverage is enforced via `backend/pyproject.toml` (`fail_under = 72`).
* Zero lint warnings tolerated under `ruff==0.8.6`.

### Frontend (Vitest + Vite)
Executed from `frontend/`:

```bash
# Run unit & component tests with coverage
pnpm run test:coverage

# Verify production bundle build
pnpm run build
```

* Test environment: `jsdom` with `@testing-library/react`.
* Enforced coverage thresholds in `frontend/vite.config.js`: Statements $\ge 38\%$, Branches $\ge 28\%$, Functions $\ge 32\%$, Lines $\ge 39\%$.

---

## Multi-User Roadmap (OpenSpec)

The system is transitioning from a single-tenant deployment to a cryptographically verified multi-tenant architecture tracked under [`openspec/changes/multi-user-foundation`](openspec/changes/multi-user-foundation/proposal.md).

| Slice | Milestone | Focus Area | Status |
| :---: | :--- | :--- | :---: |
| **S1** | **Identity Schema & Cryptography** | `users`, `user_devices`, `auth_sessions` tables + ECDSA P-256 primitives | ![Landed](https://img.shields.io/badge/status-Landed-brightgreen?style=flat-square) |
| **S2** | **Enrollment & Legacy Bootstrap** | One-shot migration of single-user data & public key device registration | ![In Progress](https://img.shields.io/badge/status-In%20Progress-yellow?style=flat-square) |
| **S3** | **Challenge & Session Lifecycle** | Cryptographic challenge/verify rounds, bearer tokens, sliding expiry | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S4** | **PAES Principal Scoping** | Removal of client-supplied `user_id` in favor of authenticated principal | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S5** | **Browser Key Management** | WebCrypto device keys in client IndexedDB; eliminate API keys from bundle | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S6** | **Auth Gate & Login Surface** | Client authentication gate preventing unauthenticated dashboard leaks | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S7** | **Ownership Migration 014** | Foreign key enforcement on all practice tables with dump verification gate | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S8** | **Peak Practice Isolation** | Gym and cognitive exercise session isolation per principal | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S9** | **Encrypted Provider Keys** | Per-user AES-256-GCM + HKDF sealed API keys for LLM providers | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S10** | **Per-Principal Router** | Dynamic credential injection into AI coach without global key caches | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |
| **S11** | **Strict Boundary Enforcement** | Full test suite execution with live identity boundaries active | ![Pending](https://img.shields.io/badge/status-Pending-lightgrey?style=flat-square) |

---

## Project Structure

```text
├── backend/
│   ├── api/            # Route handlers (auth, paes, coach, models, gym)
│   ├── core/           # Security, ECDSA crypto, database sessions, middleware
│   ├── models/         # SQLModel database schemas (identity, paes, exercises)
│   ├── services/       # Domain business logic (3PL IRT, FSRS, psychometrics)
│   ├── migrations/     # Versioned, idempotent schema migration scripts
│   └── tests/          # Pytest backend test suite (817+ tests)
├── frontend/
│   ├── src/
│   │   ├── api/        # HTTP client & backend proxy bindings
│   │   ├── components/ # Atomic UI components, PAES routine bar, exams
│   │   ├── pages/      # Route pages (PaesStudy, Gym, Settings, Dashboard)
│   │   └── store/      # Modular Zustand state management slices
│   └── vite.config.js  # Build tooling, proxies, and coverage thresholds
├── openspec/           # Spec-driven development change proposals & tasks
├── .github/workflows/  # CI pipelines with dependency caching (pip & pnpm)
├── paes.ps1            # Resilient Windows service orchestrator
└── README.md           # Repository documentation
```

---

## License

This project is licensed under the terms of the [GNU General Public License v3.0](LICENSE).
