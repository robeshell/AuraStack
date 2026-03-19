---
name: new-feature-autopilot
description: PM gives feature intent in natural language; execute end-to-end implementation for AuraStack without requiring structured requirement docs.
---

# New Feature Autopilot

Use this skill when user asks to "做XX功能", "新增模块", "加一个页面/接口", etc.

## Goal

Deliver a usable feature from intent only:

- backend API
- frontend page
- RBAC/menu wiring
- migration when needed
- OpenAPI update
- build verification

## Execution Steps

1. Identify stack + read references first
   - Confirm this project stack before implementation (Flask + React + Semi + PostgreSQL).
   - If related MCP docs/skills exist, read them first (UI tasks should prefer `semi-mcp` + `semi-design-guide`).
2. Understand intent from conversation
   - Extract actor, main workflow, key entities, and expected admin actions.
   - Make reasonable defaults for non-critical fields.
3. Scan existing modules
   - Prefer extending existing modules over creating duplicates.
4. Implement backend
   - Follow layered module structure: `backend/app/<domain>/{api,service,crud,model,schema}`.
   - Register module routes in `backend/app/<domain>/api/router.py`.
   - If introducing a new first-level domain, wire it in `backend/app/router.py` and `backend/app/__init__.py`.
   - Add/update model entities and migration when data shape changes.
5. Implement frontend
   - Add page under `frontend/src/modules/**/pages/**/index.jsx`.
   - Add API file under `frontend/src/modules/**/api/`.
   - Reuse shared request/utils from `frontend/src/shared/api/` and `frontend/src/shared/utils/`.
   - Ensure menu `path` + `component` are compatible with dynamic routing (`component` like `admin/users`, `data_management/query_management`).
   - Prefer reusing `frontend/src/shared/components/import-export/*` for import/export UX.
   - If module includes import/export, follow the existing import/export implementation pattern already used in this project.
6. Integrate permissions
   - Add menu/button permission codes.
   - Update `backend/scripts/init_rbac_data.py`.
   - Always run `python3 backend/scripts/init_rbac_data.py --incremental` after permission/menu changes.
   - The incremental mode must refresh super-admin permissions so new pages are immediately visible.
7. Update API docs
   - Edit `docs/apifox-full.openapi.json`.
8. Verify
   - Run backend compile checks.
   - Run frontend `npm run build`.
   - Optionally run `python3 backend/scripts/verify_feature.py --module <module>`.
9. Deliver handoff
   - Always provide a short "next steps" command list for the user.
   - If migration/schema changed, explicitly include `flask db upgrade -d backend/migrations` in next steps.

## Defaults (when user does not specify)

- List page supports: search + create + edit + delete.
- RBAC includes: `<module>`, `<module>_add`, `<module>_edit`, `<module>_delete`.
- New admin routes under `/api/admin/<module>`.
- Use consistent Toast success/error UX with existing pages.
- If import/export is requested, align with existing project behavior, interaction pattern, and file format conventions.

## Blocking Questions Only

Ask at most 1-2 concise questions only for:

- data model ambiguity with irreversible impact
- security-sensitive permission boundaries
- external integration credentials
