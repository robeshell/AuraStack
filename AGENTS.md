# AuraStack Agent Contract (Freedom Mode)

This repository uses **intent-driven delivery**:

- PM gives natural-language goals only.
- Agent must infer implementation details and execute end-to-end.
- Ask questions only when the decision is truly blocking.

## Tech Stack Baseline

- Backend: Flask 3 + Flask-SQLAlchemy + Flask-CORS
- Database: PostgreSQL (psycopg2)
- Frontend: React 18 + Vite + React Router + Axios
- UI Library: Semi Design (`@douyinfe/semi-ui`, `@douyinfe/semi-icons`)
- Import/Export: `openpyxl` / `xlrd` / `xlwt`

## MCP-First Reading Rule

- Before coding, identify whether related docs are available via MCP or local skills.
- For Semi UI related tasks, prefer reading Semi docs/components through `semi-mcp` first.
- If docs guidance conflicts with existing project implementation, follow existing project implementation.

## Non-Negotiable Workflow

When user says "做XX功能", the agent must complete this chain:

1. **Codebase discovery**
   - Read existing related modules before creating new files.
   - Reuse existing naming and route conventions.
2. **Backend implementation**
   - Add/update route handlers under `backend/routes/admin/`.
   - Register module in `backend/routes/admin/__init__.py` if new.
   - Update model/migration when schema changes.
3. **Frontend implementation**
   - Add/update page component under `frontend/src/pages/**/index.jsx`.
   - Add API client under `frontend/src/api/`.
   - Ensure menu path/component can be resolved by dynamic routing (`frontend/src/App.jsx`).
   - If the module has import/export, follow the existing import/export implementation pattern already used in this project.
4. **RBAC integration**
   - Add module menu + button permissions.
   - Update `scripts/init_rbac_data.py` seed data.
   - After any menu/permission change, run `python3 scripts/init_rbac_data.py --incremental`.
   - This incremental sync must include super-admin permission refresh, otherwise new features may be invisible in UI.
5. **API docs pipeline**
   - Update `docs/apifox-full.openapi.json`.
   - Keep `scripts/import_openapi_to_apifox.py` runnable.
6. **Verification**
   - Run compile/build checks.
   - Run `python3 scripts/verify_feature.py --module <module>` when applicable.
   - For import/export features, verify the implementation is consistent with existing project behavior and interaction pattern.

## Clarification Policy

The agent should not request forms/templates from PM.
Only ask concise blocking questions (max 1-2) for:

- irreversible data model choice
- external system credentials/config
- permission boundaries with security impact

## Output Policy

Deliver results in this order:

1. What changed (files)
2. What user can test now
3. Any assumptions made
4. Optional next-step options
