#!/usr/bin/env python3
"""
Import OpenAPI/Swagger data to Apifox via Open API.

Default behavior is "overwrite existing" for matched endpoints/schemas.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback path
    requests = None

API_BASE_URL = "https://api.apifox.com"
DEFAULT_API_VERSION = "2024-03-28"
OVERWRITE_BEHAVIORS = (
    "OVERWRITE_EXISTING",
    "AUTO_MERGE",
    "KEEP_EXISTING",
    "CREATE_NEW",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import OpenAPI/Swagger to Apifox project with overwrite options."
    )
    parser.add_argument(
        "--project-id",
        default=os.getenv("APIFOX_PROJECT_ID"),
        help="Apifox project ID. Default: APIFOX_PROJECT_ID env var.",
    )
    parser.add_argument(
        "--access-token",
        default=os.getenv("APIFOX_ACCESS_TOKEN"),
        help="Apifox access token. Default: APIFOX_ACCESS_TOKEN env var.",
    )
    parser.add_argument(
        "--api-version",
        default=os.getenv("APIFOX_API_VERSION", DEFAULT_API_VERSION),
        help=f"X-Apifox-Api-Version header. Default: {DEFAULT_API_VERSION}.",
    )
    parser.add_argument(
        "--locale",
        default="zh-CN",
        help="Query locale. Default: zh-CN.",
    )
    parser.add_argument(
        "--spec-file",
        default="docs/apifox-full.openapi.json",
        help="Local OpenAPI/Swagger file path for string import.",
    )
    parser.add_argument(
        "--input-url",
        default=None,
        help="Import from remote URL instead of local file.",
    )
    parser.add_argument(
        "--input-basic-auth-username",
        default=None,
        help="Optional basic auth username for --input-url.",
    )
    parser.add_argument(
        "--input-basic-auth-password",
        default=None,
        help="Optional basic auth password for --input-url.",
    )
    parser.add_argument(
        "--target-endpoint-folder-id",
        type=int,
        default=None,
        help="Target endpoint folder ID.",
    )
    parser.add_argument(
        "--target-schema-folder-id",
        type=int,
        default=None,
        help="Target schema folder ID.",
    )
    parser.add_argument(
        "--target-branch-id",
        type=int,
        default=None,
        help="Target branch ID.",
    )
    parser.add_argument(
        "--module-id",
        type=int,
        default=None,
        help="Target module ID.",
    )
    parser.add_argument(
        "--endpoint-overwrite-behavior",
        choices=OVERWRITE_BEHAVIORS,
        default="OVERWRITE_EXISTING",
        help="Overwrite behavior for endpoints.",
    )
    parser.add_argument(
        "--schema-overwrite-behavior",
        choices=OVERWRITE_BEHAVIORS,
        default="OVERWRITE_EXISTING",
        help="Overwrite behavior for schemas.",
    )
    parser.add_argument(
        "--update-folder-of-changed-endpoint",
        action="store_true",
        help="Update folder for matched endpoints after import.",
    )
    parser.add_argument(
        "--prepend-base-path",
        action="store_true",
        help="Prepend base path to endpoint paths.",
    )
    parser.add_argument(
        "--delete-unmatched-resources",
        action="store_true",
        help="Delete resources not present in imported data.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds. Default: 120.",
    )
    return parser


def _build_input(args: argparse.Namespace) -> Any:
    if args.input_url:
        input_obj: Dict[str, Any] = {"url": args.input_url}
        if args.input_basic_auth_username or args.input_basic_auth_password:
            if not (args.input_basic_auth_username and args.input_basic_auth_password):
                raise ValueError(
                    "Both --input-basic-auth-username and --input-basic-auth-password are required together."
                )
            input_obj["basicAuth"] = {
                "username": args.input_basic_auth_username,
                "password": args.input_basic_auth_password,
            }
        return input_obj

    spec_path = args.spec_file
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"OpenAPI file not found: {spec_path}")
    with open(spec_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_options(args: argparse.Namespace) -> Dict[str, Any]:
    options: Dict[str, Any] = {
        "endpointOverwriteBehavior": args.endpoint_overwrite_behavior,
        "schemaOverwriteBehavior": args.schema_overwrite_behavior,
        "updateFolderOfChangedEndpoint": args.update_folder_of_changed_endpoint,
        "prependBasePath": args.prepend_base_path,
        "deleteUnmatchedResources": args.delete_unmatched_resources,
    }
    optional_values = {
        "targetEndpointFolderId": args.target_endpoint_folder_id,
        "targetSchemaFolderId": args.target_schema_folder_id,
        "targetBranchId": args.target_branch_id,
        "moduleId": args.module_id,
    }
    for key, value in optional_values.items():
        if value is not None:
            options[key] = value
    return options


def _print_counters(counters: Optional[Dict[str, Any]]) -> None:
    if not counters:
        print("No counters returned.")
        return
    print("Import counters:")
    keys = [
        "endpointCreated",
        "endpointUpdated",
        "endpointFailed",
        "endpointIgnored",
        "schemaCreated",
        "schemaUpdated",
        "schemaFailed",
        "schemaIgnored",
        "endpointFolderCreated",
        "endpointFolderUpdated",
        "endpointFolderFailed",
        "endpointFolderIgnored",
        "schemaFolderCreated",
        "schemaFolderUpdated",
        "schemaFolderFailed",
        "schemaFolderIgnored",
    ]
    for key in keys:
        if key in counters:
            print(f"  - {key}: {counters[key]}")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if not args.project_id:
        parser.error("Missing --project-id (or APIFOX_PROJECT_ID env var).")
    if not args.access_token:
        parser.error("Missing --access-token (or APIFOX_ACCESS_TOKEN env var).")

    try:
        input_payload = _build_input(args)
    except Exception as exc:
        print(f"Input build failed: {exc}", file=sys.stderr)
        return 1

    url = f"{API_BASE_URL}/v1/projects/{args.project_id}/import-openapi"
    headers = {
        "Authorization": f"Bearer {args.access_token}",
        "X-Apifox-Api-Version": args.api_version,
        "Content-Type": "application/json",
    }
    payload = {
        "input": input_payload,
        "options": _build_options(args),
    }
    params = {"locale": args.locale}

    status_code: int
    body: Dict[str, Any]

    if requests is not None:
        try:
            resp = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=args.timeout,
            )
            status_code = resp.status_code
            try:
                body = resp.json()
            except ValueError:
                body = {"raw": resp.text}
        except requests.RequestException as exc:
            print(f"Request failed: {exc}", file=sys.stderr)
            return 1
    else:
        final_url = f"{url}?{urllib.parse.urlencode(params)}"
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            final_url,
            data=data_bytes,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                status_code = resp.getcode()
                text = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            text = exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            print(f"Request failed: {exc}", file=sys.stderr)
            return 1

        try:
            body = json.loads(text)
        except ValueError:
            body = {"raw": text}

    if status_code >= 400:
        print(f"Import failed. HTTP {status_code}", file=sys.stderr)
        print(json.dumps(body, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print("Import request accepted.")
    print(json.dumps(body, ensure_ascii=False, indent=2))

    data = body.get("data", {}) if isinstance(body, dict) else {}
    counters = data.get("counters") if isinstance(data, dict) else None
    errors = data.get("errors") if isinstance(data, dict) else None
    _print_counters(counters)

    if isinstance(errors, list) and errors:
        print("Import returned errors:", file=sys.stderr)
        for item in errors:
            message = item.get("message", "") if isinstance(item, dict) else str(item)
            code = item.get("code", "") if isinstance(item, dict) else ""
            print(f"  - code={code} message={message}", file=sys.stderr)
        return 2

    failed_count = 0
    if isinstance(counters, dict):
        failed_count += int(counters.get("endpointFailed", 0) or 0)
        failed_count += int(counters.get("schemaFailed", 0) or 0)
        failed_count += int(counters.get("endpointFolderFailed", 0) or 0)
        failed_count += int(counters.get("schemaFolderFailed", 0) or 0)
    if failed_count > 0:
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
