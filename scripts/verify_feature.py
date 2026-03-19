#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feature verification helper for AuraStack.

Purpose:
- Provide a quick, deterministic check after AI implements a feature/module.
- Keep PM flow free: no templates/forms required.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "venv" / "bin" / "python"
PYTHON_BIN = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    process = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process.returncode, process.stdout


def check_file_exists(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"Missing file: {path.relative_to(ROOT)}")


def to_pascal_case(name: str) -> str:
    parts = re.split(r"[_\-\s]+", name.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def verify_module(module: str, errors: list[str], warnings: list[str]) -> None:
    module = module.strip().lower()
    pascal = to_pascal_case(module)

    backend_route = ROOT / "backend" / "routes" / "admin" / f"{module}.py"
    frontend_api = ROOT / "frontend" / "src" / "api" / f"{module}.js"
    frontend_page = ROOT / "frontend" / "src" / "pages" / "System" / pascal / "index.jsx"

    check_file_exists(backend_route, errors)
    check_file_exists(frontend_api, errors)
    check_file_exists(frontend_page, errors)

    admin_init = ROOT / "backend" / "routes" / "admin" / "__init__.py"
    if admin_init.exists():
        content = admin_init.read_text(encoding="utf-8")
        if module not in content:
            warnings.append(
                f"`backend/routes/admin/__init__.py` may not register module `{module}`."
            )

    seed_file = ROOT / "scripts" / "init_rbac_data.py"
    if seed_file.exists():
        seed_text = seed_file.read_text(encoding="utf-8")
        expected_codes = [
            f"system_{module}",
            f"system_{module}_add",
            f"system_{module}_edit",
            f"system_{module}_delete",
        ]
        missing = [code for code in expected_codes if code not in seed_text]
        if missing:
            warnings.append(
                "RBAC seed may be incomplete, missing permission codes: "
                + ", ".join(missing)
            )
        if "--incremental" not in seed_text or "refresh_super_admin_permissions" not in seed_text:
            warnings.append(
                "`scripts/init_rbac_data.py` should support incremental menu sync "
                "and super-admin permission refresh."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify feature/module integration in AuraStack.")
    parser.add_argument("--module", help="Module name in snake_case, e.g. notifications")
    parser.add_argument("--skip-build", action="store_true", help="Skip frontend build check")
    parser.add_argument(
        "--run-rbac-sync",
        action="store_true",
        help="Run `python3 scripts/init_rbac_data.py --incremental` during verification.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if args.module:
        verify_module(args.module, errors, warnings)

    print("== AuraStack feature verification ==")

    compile_targets = [
        "app.py",
        "backend/models.py",
        "backend/common/tabular.py",
        "backend/routes/admin/auth.py",
        "backend/routes/admin/users.py",
        "backend/routes/admin/roles.py",
        "backend/routes/admin/menus.py",
        "backend/routes/admin/logs.py",
        "backend/routes/admin/dicts.py",
        "backend/routes/admin/query_management.py",
        "scripts/init_rbac_data.py",
        "scripts/import_openapi_to_apifox.py",
    ]
    code, output = run([PYTHON_BIN, "-m", "py_compile", *compile_targets])
    if code != 0:
        errors.append("Python compile check failed.")
        print(output)
    else:
        print("Python compile check: OK")

    openapi_file = ROOT / "docs" / "apifox-full.openapi.json"
    if openapi_file.exists():
        print("OpenAPI file exists: OK")
    else:
        errors.append("Missing docs/apifox-full.openapi.json")

    if args.run_rbac_sync:
        code, output = run([PYTHON_BIN, "scripts/init_rbac_data.py", "--incremental"])
        if code != 0:
            errors.append("RBAC incremental sync failed.")
            print(output)
        else:
            print("RBAC incremental sync: OK")
    else:
        print("RBAC visibility step: run `./venv/bin/python scripts/init_rbac_data.py --incremental`")

    if not args.skip_build:
        code, output = run(["npm", "run", "build"], cwd=ROOT / "frontend")
        if code != 0:
            errors.append("Frontend build failed.")
            print(output)
        else:
            print("Frontend build: OK")

    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("\nAll critical checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
