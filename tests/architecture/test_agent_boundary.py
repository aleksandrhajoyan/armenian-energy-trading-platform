"""Application agent contract remains framework-neutral and structurally typed."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_http_api_import_violations,
    collect_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

AGENTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "agents"
AGENT_BASE = AGENTS_ROOT / "base.py"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.domain",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "qdrant_client",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "lightgbm",
    "xgboost",
    "sklearn",
    "torch",
    "tensorflow",
    "httpx",
    "requests",
    "aiohttp",
    "n8n",
)

FORBIDDEN_CONTRACT_NAMES = frozenset(
    {
        "Any",
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "state",
        "context",
        "callbacks",
        "callback_manager",
        "tools",
        "messages",
        "model",
        "prompt",
        "ABC",
        "abstractmethod",
        "BaseAgent",
        "AbstractAgent",
        "AgentRegistry",
        "AgentFactory",
        "AgentResult",
        "AgentResponse",
        "OrchestrationState",
        "GraphState",
        "WorkflowState",
        "Request",
        "Response",
    }
)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _function(
    class_def: ast.ClassDef, function_name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    msg = f"function {function_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def _identifier_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
            names.update(arg.arg for arg in node.args.args)
            names.update(arg.arg for arg in node.args.kwonlyargs)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            names.update(param.name for param in node.type_params)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def test_agent_base_does_not_import_outer_layers_or_vendors() -> None:
    package_forbidden = tuple(
        prefix for prefix in FORBIDDEN_PREFIXES if prefix != "energy_trading.domain"
    )
    assert collect_import_violations(AGENTS_ROOT, package_forbidden) == []
    leaked_base = [
        f"{AGENT_BASE.relative_to(SRC_ROOT)} imports {module}"
        for module in sorted(imported_modules(AGENT_BASE))
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    ]
    assert leaked_base == []
    leaked = sorted(name for name in imported_names(AGENT_BASE) if name in FORBIDDEN_CONTRACT_NAMES)
    assert leaked == []
    allowed = {"enum", "StrEnum", "typing", "Protocol"}
    extras = imported_names(AGENT_BASE) - allowed
    assert extras == set()


def test_agent_port_is_generic_protocol_not_abc() -> None:
    class_def = _class_def(AGENT_BASE, "AgentPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert [param.name for param in class_def.type_params] == ["TRequest", "TResult"]
    source = AGENT_BASE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "ABC" not in source


def test_agent_port_exposes_only_name_and_async_run() -> None:
    class_def = _class_def(AGENT_BASE, "AgentPort")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["name", "run"]
    name_fn = _function(class_def, "name")
    assert isinstance(name_fn, ast.FunctionDef)
    assert any(
        isinstance(item, ast.Name) and item.id == "property" for item in name_fn.decorator_list
    )
    assert tuple(arg.arg for arg in name_fn.args.args) == ("self",)
    run_fn = _function(class_def, "run")
    assert isinstance(run_fn, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "request")
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert tuple(arg.arg for arg in run_fn.args.kwonlyargs) == ()
    assert async_function_arg_names(AGENT_BASE, "run") == ("self", "request")


def test_agent_public_contract_excludes_framework_and_payload_types() -> None:
    names = annotation_type_names(AGENT_BASE)
    leaked_annotations = sorted(name for name in names if name in FORBIDDEN_CONTRACT_NAMES)
    assert leaked_annotations == []
    assert "AgentName" in names
    assert "TRequest" in names
    assert "TResult" in names
    identifiers = _identifier_names(AGENT_BASE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_CONTRACT_NAMES)
    assert leaked_identifiers == []


def test_agent_name_enum_is_defined_in_application() -> None:
    class_def = _class_def(AGENT_BASE, "AgentName")
    bases = _base_names(class_def)
    assert "StrEnum" in bases
    members = [
        node.targets[0].id
        for node in class_def.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    ]
    assert len(members) == 13


def test_api_composition_does_not_import_or_construct_agents() -> None:
    forbidden_wiring = (
        "energy_trading.application.agents",
        "energy_trading.application.agents.base",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "AgentPort" not in names
        assert "AgentName" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "agentport" not in app_source
    assert "agentname" not in app_source
