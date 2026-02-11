# K24 Agent Roles & Workflow

## 1. Agent Roster (Phase 1)

We use three main agents:

1. Planner (Architecture & Design)
2. Builder+MCPS (Implementation & cross-platform debugging)
3. Tester/Reviewer (Quality, security, and verification)

You (founder) are the orchestrator. You decide tasks and approve risky changes.

---

## 2. Planner

**Goal:** Design clear, small plans and contracts so other agents can build safely.

**Responsibilities**

- Understand the current architecture (desktop sidecar, cloud, Tauri, WhatsApp, Tally).
- Decide what belongs on cloud vs local, consistent with `contracts.md`.
- Write and update:
  - `plan.md` (current phase, steps),
  - `contracts.md` (flows and schemas),
  - relevant sections of `CLAUDE.md` when patterns change.
- Break work into tasks with explicit file paths and acceptance criteria.

**Allowed to touch**

- `CLAUDE.md`, `agents.md`, `contracts.md`, `plan.md`.
- Other `*.md` docs.
- SQL schema files when designing (not blindly migrating).

**Not allowed**

- Changing `.py`, `.ts`, `.tsx` implementation code.
- Editing secrets or deployment configuration.

**Handoff**

- Each task for Builder must state:
  - files to edit,
  - behavior required,
  - tests to add/run,
  - anything that needs founder approval.

---

## 3. Builder + MCPS

**Goal:** Implement tasks end-to-end and fix issues across cloud + desktop using tools.

**Responsibilities**

- Implement cloud WhatsApp queue, desktop poller, and glue code as per `plan.md` and `contracts.md`.
- Wire and use MCP tools for:
  - Supabase DB,
  - Vercel / cloud logs,
  - Railway deployments / DB (when used).
- Fix auth/deeplink and installer-related issues without changing the overall auth model.
- Keep changes small and focused; avoid touching high-risk zones unless approved.

**Allowed to touch**

- Cloud backend:
  - `cloud-backend/routers/*.py`
  - `cloud-backend/services/*.py`
  - `cloud-backend/database/supabase_client.py`
  - Supabase migrations for WhatsApp queue and tenant routing.
- Desktop backend:
  - `backend/routers/*.py` (except auth/Tally files flagged in `CLAUDE.md`)
  - `backend/services/*.py` (new poller, glue)
  - `backend/desktop_main.py` (startup integration)
- Frontend where needed for auth/deeplink UX (but not middleware rules).

**Special rule: sensitive areas**

Before touching any of these, Builder must ask the founder:

- `backend/tally_*` files.
- `backend/services/tally_operations.py`.
- `backend/auth.py`, `cloud-backend/routers/auth.py`.
- `frontend/src/middleware.ts`.

**Testing expectation**

- For every feature:
  - Implement tests or update existing ones.
  - Run them and document results.
  - Trigger at least one realistic flow (e.g., WhatsApp message through queue) to confirm.

---

## 4. Tester / Reviewer

**Goal:** Protect quality and security without blocking speed.

**Responsibilities**

- Write and extend unit/tests/integration tests for:
  - WhatsApp → cloud → desktop → Tally flow.
  - Auth + deep link.
  - Tenant isolation.
- Run test suites and summarise results for the founder.
- Review diffs for:
  - Security issues,
  - Tenant isolation problems,
  - Contract breaks against `contracts.md`.

**Allowed to touch**

- `tests/**`, `test_*.py`, `verify_*.py`.
- Test fixtures and helper scripts.
- Comments and minor annotations in production code if needed for testing.

**Not allowed**

- Large changes to production logic.
- Changing schema or contracts without Planner involvement.

**Review checklist**

- Queries and APIs respect `tenant_id` and RLS.
- No high-risk files were changed without explicit note.
- API requests/responses match `contracts.md`.
- Tests cover the new behavior and pass.

---

## 5. Workflow Summary

For each feature / bugfix:

1. **Planner**
   - Updates `plan.md` with a small, concrete task.
   - References `contracts.md` and gives file paths.

2. **Builder+MCPS**
   - Reads `CLAUDE.md`, `agents.md`, `contracts.md`, `plan.md`.
   - Implements code in the allowed area.
   - Uses tools (Supabase, Vercel, Railway) to verify end-to-end behavior.
   - Runs tests requested by Planner and records results.

3. **Tester/Reviewer**
   - Adds extra tests if needed.
   - Runs broader test suites.
   - Reviews diffs for security and correctness.
   - Flags any change that touches protected zones.

4. **Founder**
   - Approves or rejects risky changes.
   - Decides when Phase 1 goals in `plan.md` are achieved.
