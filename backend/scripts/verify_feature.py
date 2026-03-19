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
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
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


def verify_module(module: str, errors: list[str], warnings: list[str]) -> None:
    module = module.strip().lower()
    singular = module[:-1] if module.endswith("s") else module

    backend_candidates = [
        ROOT / "backend" / "app" / "admin" / "api" / f"{module}.py",
        ROOT / "backend" / "app" / "admin" / "api" / f"{singular}.py",
        ROOT / "backend" / "app" / module / "api" / f"{module}.py",
        ROOT / "backend" / "app" / module / "api" / f"{singular}.py",
        ROOT / "backend" / "app" / singular / "api" / f"{singular}.py",
    ]
    # 一级模块是 data_management，query_management 属于该大模块
    if module in {"query_management", "query-management"}:
        backend_candidates.extend([
            ROOT / "backend" / "app" / "data_management" / "api" / "query_management.py",
            ROOT / "backend" / "app" / "data_management" / "api" / "query-management.py",
        ])
    if module in {"scheduled_tasks", "scheduled-task", "scheduled-tasks"}:
        backend_candidates.extend([
            ROOT / "backend" / "app" / "admin" / "api" / "scheduled_task.py",
            ROOT / "backend" / "app" / "admin" / "api" / "scheduled-task.py",
            ROOT / "backend" / "app" / "admin" / "api" / "scheduled_tasks.py",
        ])
    frontend_api_candidates = [
        ROOT / "frontend" / "src" / "modules" / "admin" / "api" / f"{module}.js",
        ROOT / "frontend" / "src" / "modules" / "admin" / "api" / f"{singular}.js",
        ROOT / "frontend" / "src" / "modules" / "data_management" / "api" / f"{module}.js",
        ROOT / "frontend" / "src" / "modules" / "data_management" / "api" / f"{singular}.js",
    ]
    frontend_page_candidates = [
        ROOT / "frontend" / "src" / "modules" / "admin" / "pages" / module / "index.jsx",
        ROOT / "frontend" / "src" / "modules" / "admin" / "pages" / singular / "index.jsx",
        ROOT / "frontend" / "src" / "modules" / "data_management" / "pages" / module / "index.jsx",
        ROOT / "frontend" / "src" / "modules" / "data_management" / "pages" / singular / "index.jsx",
    ]

    if not any(path.exists() for path in backend_candidates):
        errors.append(
            "Missing backend entry: expected one of "
            + ", ".join(str(path.relative_to(ROOT)) for path in backend_candidates)
        )
    if not any(path.exists() for path in frontend_api_candidates):
        errors.append(
            "Missing frontend API entry: expected one of "
            + ", ".join(str(path.relative_to(ROOT)) for path in frontend_api_candidates)
        )
    if not any(path.exists() for path in frontend_page_candidates):
        errors.append(
            "Missing frontend page entry: expected one of "
            + ", ".join(str(path.relative_to(ROOT)) for path in frontend_page_candidates)
        )

    router_files = [
        ROOT / "backend" / "app" / "router.py",
        ROOT / "backend" / "app" / "admin" / "api" / "router.py",
        ROOT / "backend" / "app" / "data_management" / "api" / "router.py",
    ]
    combined_router_text = ""
    for file in router_files:
        if file.exists():
            combined_router_text += "\n" + file.read_text(encoding="utf-8")

    if module not in combined_router_text and singular not in combined_router_text:
        warnings.append(
            f"`backend/app/**/router.py` may not register module `{module}`."
        )

    seed_file = ROOT / "backend" / "scripts" / "init_rbac_data.py"
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
                "`backend/scripts/init_rbac_data.py` should support incremental menu sync "
                "and super-admin permission refresh."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify feature/module integration in AuraStack.")
    parser.add_argument("--module", help="Module name in snake_case, e.g. notifications")
    parser.add_argument("--skip-build", action="store_true", help="Skip frontend build check")
    parser.add_argument(
        "--run-rbac-sync",
        action="store_true",
        help="Run `python3 backend/scripts/init_rbac_data.py --incremental` during verification.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if args.module:
        verify_module(args.module, errors, warnings)

    print("== AuraStack feature verification ==")

    compile_targets = [
        "app.py",
        "backend/__init__.py",
        "backend/scripts/init_rbac_data.py",
        "backend/scripts/import_openapi_to_apifox.py",
    ]
    for layer_dir in ["backend/common", "backend/app"]:
        base = ROOT / layer_dir
        if not base.exists():
            warnings.append(f"Missing layer directory: {layer_dir}")
            continue
        for path in sorted(base.rglob("*.py")):
            compile_targets.append(str(path.relative_to(ROOT)))
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
        code, output = run([PYTHON_BIN, "backend/scripts/init_rbac_data.py", "--incremental"])
        if code != 0:
            errors.append("RBAC incremental sync failed.")
            print(output)
        else:
            print("RBAC incremental sync: OK")
    else:
        print("RBAC visibility step: run `./venv/bin/python backend/scripts/init_rbac_data.py --incremental`")

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
