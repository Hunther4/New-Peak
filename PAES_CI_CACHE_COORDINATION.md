# PAES CI-Cache Coordination Ledger (vertical alliance)

Protocol (owner-mandated):

- Agents and workers NEVER push to `origin/main`. The owner is the last mile who pushes.
- Backend/frontend workers deliver CI-cache changes pre-staged via `git worktree` in isolation.
- Before any push that touches `.github/workflows/*`, an actor appends an entry here:
  date · sha256 of the modified file · commit hash and message · actor.
- The sha256 is the "anchor": if it changes, every actor must re-read `ci.yml` before touching it.
- No synthetic claims: every entry reports the verified state of the file, not intent.

## Anchors

- 2026-10-22 · `sha256:e7671b7fea9843827e02bc6c528b8b6fe3abfc8656588cade34ab353fde057a9` (.github/workflows/ci.yml) · commit `e427ec3` "perf(ci): enable pip and pnpm caching in GitHub Actions" · pushed to origin/main by owner Hunther4. Orchestrator verified the file state: `actions/setup-python@v5` has `cache: "pip"` + `cache-dependency-path: backend/requirements.txt` (lines 23-24); `actions/setup-node@v4` has `cache: "pnpm"` + `cache-dependency-path: frontend/pnpm-lock.yaml` (lines 54-55).
