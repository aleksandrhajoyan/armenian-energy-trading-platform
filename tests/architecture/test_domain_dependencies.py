"""Domain layer must not depend on outer packages or FastAPI."""

from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_ROOT = Path(__file__).resolve().parents[2] / "src" / "energy_trading" / "domain"
SRC_ROOT = DOMAIN_ROOT.parents[1]

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.application",
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.shared",
    "fastapi",
)


def _module_from_file(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT).with_suffix("")
    return ".".join(relative.parts)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    current_module = _module_from_file(path)
    current_parts = current_module.split(".")
    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module is not None:
                    imported.add(node.module)
                continue
            parent_parts = current_parts[: -node.level]
            if node.module:
                imported.add(".".join((*parent_parts, *node.module.split("."))))
            elif parent_parts:
                imported.add(".".join(parent_parts))

    return imported


def _is_forbidden(module: str) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in FORBIDDEN_PREFIXES)


def test_domain_does_not_import_outer_layers_or_fastapi() -> None:
    violations: list[str] = []
    for path in sorted(DOMAIN_ROOT.rglob("*.py")):
        for module in sorted(_imported_modules(path)):
            if _is_forbidden(module):
                violations.append(f"{path.relative_to(SRC_ROOT)} imports {module}")

    assert violations == []
