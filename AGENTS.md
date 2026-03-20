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
- Migrations directory: `backend/migrations/`
- Engineering scripts: `backend/scripts/`

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
   - Implement under layered module structure: `backend/app/<domain>/{api,service,crud,model,schema}`.
   - Register module routes in `backend/app/<domain>/api/router.py`.
   - If introducing a new first-level domain, wire it in `backend/app/router.py` and `backend/app/__init__.py`.
   - In API layer, use unified permission helpers from `backend/common/auth.py` (`has_menu_permission` / `has_any_menu_permission` / `menu_permission_required`).
   - Do not define per-file local `has_permission` in API modules.
   - Update model entities and migration when schema changes.
3. **Frontend implementation**
   - Add/update page component under `frontend/src/modules/**/pages/**/index.jsx`.
   - Add API client under `frontend/src/modules/**/api/` (shared request client in `frontend/src/shared/api/`).
   - Ensure menu path/component can be resolved by dynamic routing (`frontend/src/App.jsx`).
   - Menu component value should align with `modules/**/pages/**/index.jsx` suffix (e.g. `admin/users`, `data_management/query_management`).
   - Prefer reusing existing import/export components under `frontend/src/shared/components/import-export/`.
   - If the module has import/export, follow the existing import/export implementation pattern already used in this project.
4. **RBAC integration**
   - Add module menu + button permissions.
   - Update `backend/scripts/init_rbac_data.py` seed data.
   - After any menu/permission change, run `python3 backend/scripts/init_rbac_data.py --incremental`.
   - This incremental sync must include super-admin permission refresh, otherwise new features may be invisible in UI.
5. **API docs pipeline**
   - Update `docs/apifox-full.openapi.json`.
   - Keep `backend/scripts/import_openapi_to_apifox.py` runnable.
6. **Verification**
   - Run compile/build checks.
   - Run `python3 backend/scripts/verify_feature.py --module <module>` when applicable.
   - For import/export features, verify the implementation is consistent with existing project behavior and interaction pattern.
7. **Delivery guidance**
   - Always tell the user the next executable steps after feature delivery.
   - If schema/migration changed, explicitly remind the user to run `flask db upgrade -d backend/migrations`.

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
3. Next steps user should run now (commands)
4. Any assumptions made
5. Optional next-step options
