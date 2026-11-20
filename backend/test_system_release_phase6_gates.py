"""Phase 6 system integration and release-readiness gates.

These tests verify cross-layer contracts without contacting production services.
They do not prove that Supabase migrations have been applied or that deployment is live.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "main.py"
OPENAPI = ROOT / "docs" / "api" / "openapi.json"
ENDPOINT_DOC = ROOT / "docs" / "api" / "API_ENDPOINTS.md"
MIGRATIONS = ROOT / "supabase" / "migrations"


def _main_source():
    return MAIN.read_text(encoding="utf-8-sig")


def _route_inventory():
    tree = ast.parse(_main_source())
    routes = {}
    handlers = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
                continue
            if func.value.id != "app" or func.attr.lower() not in {
                "get", "post", "put", "patch", "delete", "options", "head"
            }:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            path = decorator.args[0].value
            method = func.attr.lower()
            routes.setdefault(path, set()).add(method)
            handlers[(path, method)] = node
    return routes, handlers


def _has_current_user_dependency(function):
    for arg in function.args.args + function.args.kwonlyargs:
        if arg.arg != "user":
            continue
        if arg in function.args.args:
            index = function.args.args.index(arg)
            defaults = function.args.defaults
            default_index = index - (len(function.args.args) - len(defaults))
            default = defaults[default_index] if default_index >= 0 else None
        else:
            index = function.args.kwonlyargs.index(arg)
            default = function.args.kw_defaults[index]
        if isinstance(default, ast.Call) and isinstance(default.func, ast.Name):
            if default.func.id == "Depends" and default.args:
                dep = default.args[0]
                if isinstance(dep, ast.Name) and dep.id == "get_current_user":
                    return True
    return False


def test_fastapi_route_inventory_matches_openapi_contract():
    source_routes, _ = _route_inventory()
    spec = json.loads(OPENAPI.read_text(encoding="utf-8-sig"))
    spec_routes = {
        path: {method for method in methods if method in {
            "get", "post", "put", "patch", "delete", "options", "head"
        }}
        for path, methods in spec["paths"].items()
    }
    assert source_routes, "No FastAPI route decorators found"
    assert source_routes == spec_routes, (
        f"Route/OpenAPI drift. Source-only={source_routes.keys() - spec_routes.keys()}, "
        f"OpenAPI-only={spec_routes.keys() - source_routes.keys()}"
    )


def test_every_non_public_api_route_requires_authenticated_user():
    _, handlers = _route_inventory()
    public = {("/", "get"), ("/health", "get"), ("/public-config", "get")}
    protected = set(handlers) - public
    assert protected, "No protected routes discovered"
    missing = [
        f"{method.upper()} {path}"
        for path, method in protected
        if not _has_current_user_dependency(handlers[(path, method)])
    ]
    assert not missing, f"Routes missing get_current_user dependency: {missing}"


def test_companion_and_agent_routes_derive_owner_from_authenticated_user():
    source = _main_source()
    assert "user_id = str(user.id)" in source
    assert "str(user.id), request.scope" in source
    assert "str(user.id), scope=request.scope" in source
    assert "str(user.id), title=request.title" in source
    assert "user_id=str(user.id)" in source
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in {
            "ConsentRequest", "ContextRequest", "NeedRequest",
            "NeedUpdateRequest", "FollowUpRequest", "ProactiveEventRequest",
            "ProposalStatusRequest", "AgentTaskRequest", "ChatRequest",
        }:
            fields = {
                item.target.id for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
            assert "user_id" not in fields, f"{node.name} accepts user_id from request"


def test_public_config_does_not_return_server_secrets():
    source = _main_source()
    match = re.search(
        r"def public_config\(\):(?P<body>.*?)(?=\n\n@app\.|\Z)",
        source, re.S
    )
    assert match, "public_config endpoint not found"
    body = match.group("body")
    assert "SUPABASE_URL" in body
    assert "SUPABASE_PUBLISHABLE_KEY" in body
    assert "SUPABASE_SECRET_KEY" not in body
    assert "GEMINI_API_KEY" not in body


def test_backend_secret_key_is_loaded_server_side_not_exposed_by_frontend_config():
    source = _main_source()
    assert 'os.environ["SUPABASE_SECRET_KEY"]' in source
    assert "db_client = create_client(" in source
    public_config = re.search(
        r"def public_config\(\):(?P<body>.*?)(?=\n\n@app\.|\Z)",
        source, re.S
    ).group("body")
    assert "db_client" not in public_config


def test_cors_uses_explicit_origin_allowlist_and_does_not_allow_wildcard_credentials():
    source = _main_source()
    assert "allow_origins=CORS_ORIGINS" in source
    assert "allow_credentials=True" in source
    assert 'allow_origins=["*"]' not in source
    assert 'allow_origins=["*"],' not in source


def test_companion_and_agent_persistence_migrations_exist_in_order():
    files = sorted(p.name for p in MIGRATIONS.glob("*.sql"))
    required = [
        "202611180001_companion_persistence.sql",
        "202611180002_agent_memory_engine.sql",
        "202611180003_memory_intelligence_layer.sql",
        "202611190001_memory_transactional_write.sql",
        "202611190002_memory_transactional_review_delete.sql",
    ]
    for name in required:
        assert name in files, f"Missing migration: {name}"
    assert [files.index(name) for name in required] == sorted(
        files.index(name) for name in required
    )


def test_companion_persistence_migration_documents_service_role_and_owner_checks():
    path = MIGRATIONS / "202611180001_companion_persistence.sql"
    sql = path.read_text(encoding="utf-8-sig").lower()
    assert "service_role" in sql or "secret key" in sql
    assert "user_id" in sql
    assert "row level security" in sql or "enable row level security" in sql
    assert "never trust user_id from request body" in sql or "không tin user_id từ request body" in sql


def test_memory_transactional_functions_are_not_executable_by_public_clients():
    write_sql = (MIGRATIONS / "202611190001_memory_transactional_write.sql").read_text(
        encoding="utf-8-sig"
    ).lower()
    review_sql = (MIGRATIONS / "202611190002_memory_transactional_review_delete.sql").read_text(
        encoding="utf-8-sig"
    ).lower()
    assert "revoke all on function public.memory_write_with_audit" in write_sql
    assert "from public, anon, authenticated" in write_sql
    assert "grant execute" in write_sql and "to service_role" in write_sql
    assert "revoke all on function public.memory_update_with_audit" in review_sql
    assert "from public, anon, authenticated" in review_sql
    assert "grant execute" in review_sql and "to service_role" in review_sql


def test_api_documentation_and_deployment_status_are_explicit():
    endpoint_doc = ENDPOINT_DOC.read_text(encoding="utf-8-sig")
    deployment_doc = (ROOT / "docs" / "DEPLOYMENT.md").read_text(
        encoding="utf-8-sig"
    )
    assert "Generated from openapi.json" in endpoint_doc
    assert "Chưa triển khai" in deployment_doc or "Not deployed" in deployment_doc


def test_backend_dependencies_declare_runtime_frameworks():
    requirements = (ROOT / "backend" / "requirements.txt").read_text(
        encoding="utf-8-sig"
    ).lower()
    for dependency in ("fastapi", "uvicorn", "supabase", "pydantic", "python-dotenv"):
        assert dependency in requirements