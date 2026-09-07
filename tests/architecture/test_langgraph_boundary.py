"""LangGraph belongs only to the application orchestration graph module."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
AGENT_BASE = AGENTS_ROOT / "base.py"
PORTS_ROOT = PRODUCTION_ROOT / "application" / "ports"
USE_CASES_ROOT = PRODUCTION_ROOT / "application" / "use_cases"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_GRAPH_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "fastapi",
    "starlette",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "redis",
    "qdrant_client",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
    "requests",
    "aiohttp",
    "pandas",
    "openpyxl",
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "n8n",
)

FORBIDDEN_GRAPH_NAMES = frozenset(
    {
        "MessagesState",
        "MessageGraph",
        "add_messages",
        "Command",
        "Send",
        "RetryPolicy",
        "MemorySaver",
        "InMemorySaver",
        "BaseStore",
        "BaseCache",
        "add_conditional_edges",
        "entrypoint",
        "task",
        "interrupt",
        "AgentPort",
        "AgentName",
        "Any",
    }
)

ALLOWED_GRAPH_IMPORTS = frozenset(
    {
        "langgraph.graph",
        "langgraph.graph.state",
        "energy_trading.application.orchestration.state",
        "END",
        "START",
        "StateGraph",
        "CompiledStateGraph",
        "WorkflowState",
    }
)


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
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
    return names


def test_langgraph_imports_are_confined_to_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []


def test_state_module_remains_langgraph_free() -> None:
    names = imported_names(STATE_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(STATE_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_policy_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_POLICY_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    assert "RetryPolicy" not in names
    modules = imported_modules(FAILURE_POLICY_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_agent_base_remains_langgraph_free() -> None:
    assert (
        collect_import_violations(AGENTS_ROOT, ("langgraph", "langchain", "langchain_core")) == []
    )
    names = imported_names(AGENT_BASE)
    assert "langgraph" not in names
    assert "StateGraph" not in names


def test_other_layers_do_not_import_langgraph() -> None:
    forbidden = ("langgraph", "langchain", "langchain_core")
    for root in (
        PRODUCTION_ROOT / "domain",
        PRODUCTION_ROOT / "infrastructure",
        PRODUCTION_ROOT / "ml",
        API_ROOT,
        PORTS_ROOT,
        USE_CASES_ROOT,
    ):
        assert collect_import_violations(root, forbidden) == []


def test_graph_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(GRAPH_MODULE)
        if is_forbidden(module, FORBIDDEN_GRAPH_PREFIXES)
    )
    assert leaked == []
    extras = imported_names(GRAPH_MODULE) - ALLOWED_GRAPH_IMPORTS
    assert extras == set()


def test_graph_module_uses_only_workflow_state_contract() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "WorkflowState" in names
    assert "WorkflowPhase" not in names
    assert "WorkflowStatus" not in names
    assert "AgentPort" not in names
    assert "AgentName" not in names
    assert "ParallelIngestionPlan" not in names
    assert "ParallelIngestionSuccess" not in names
    assert "ParallelIngestionExecutionPort" not in names
    assert "ParallelIngestionWorkflowContextPort" not in names
    assert "ParallelIngestionWorkflowStep" not in names
    assert "ConcurrentParallelIngestionExecutor" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.parallel_ingestion" not in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_context" not in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_executor" not in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_workflow" not in modules


def test_graph_module_excludes_forbidden_runtime_features() -> None:
    identifiers = _identifier_names(GRAPH_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_GRAPH_NAMES)
    assert leaked == []
    imported = imported_names(GRAPH_MODULE)
    leaked_imports = sorted(name for name in imported if name in FORBIDDEN_GRAPH_NAMES)
    assert leaked_imports == []
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    call_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "add_conditional_edges" not in call_names
    assert "compile" in call_names
    compile_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "compile"
    ]
    assert len(compile_calls) == 1
    compile_call = compile_calls[0]
    assert compile_call.args == []
    assert compile_call.keywords == []


def test_graph_module_has_no_type_ignore_or_private_langgraph_imports() -> None:
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(GRAPH_MODULE), type_comments=True)
    assert tree.type_ignores == []
    assert "Any" not in _identifier_names(GRAPH_MODULE)
    private_imports = sorted(module for module in imported_modules(GRAPH_MODULE) if "._" in module)
    assert private_imports == []


def test_api_composition_does_not_import_or_construct_graph() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.graph",
        "langgraph",
        "langchain",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "build_workflow_graph" not in app_source
    assert "langgraph" not in app_source
    assert "workflow_entry" not in app_source
