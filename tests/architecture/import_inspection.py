"""AST helpers for architecture import-direction tests."""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"


def module_from_file(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT).with_suffix("")
    return ".".join(relative.parts)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    current_module = module_from_file(path)
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


def is_forbidden(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


def collect_import_violations(root: Path, prefixes: tuple[str, ...]) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, prefixes):
                violations.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    return violations
