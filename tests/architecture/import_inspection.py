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


def imported_names(path: Path) -> set[str]:
    """Return imported module paths and bound names (including ``from x import Y``)."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
                names.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
                if alias.asname is not None:
                    names.add(alias.asname)
    return names


def _collect_annotation_names(node: ast.AST | None, names: set[str]) -> None:
    if node is None:
        return
    if isinstance(node, ast.Name):
        names.add(node.id)
        return
    if isinstance(node, ast.Attribute):
        names.add(node.attr)
        _collect_annotation_names(node.value, names)
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        names.add(node.value)
        return
    for child in ast.iter_child_nodes(node):
        _collect_annotation_names(child, names)


def annotation_type_names(path: Path) -> set[str]:
    """Return simple type names used in annotations, bases, and type-parameter bounds."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for type_param in node.type_params:
                _collect_annotation_names(getattr(type_param, "bound", None), names)
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                _collect_annotation_names(arg.annotation, names)
            if node.args.vararg is not None:
                _collect_annotation_names(node.args.vararg.annotation, names)
            if node.args.kwarg is not None:
                _collect_annotation_names(node.args.kwarg.annotation, names)
            _collect_annotation_names(node.returns, names)
        elif isinstance(node, ast.AnnAssign):
            _collect_annotation_names(node.annotation, names)
        elif isinstance(node, ast.ClassDef):
            for base in node.bases:
                _collect_annotation_names(base, names)
            for type_param in node.type_params:
                _collect_annotation_names(getattr(type_param, "bound", None), names)
        elif isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name == "TypeVar":
                for keyword in node.keywords:
                    if keyword.arg == "bound":
                        _collect_annotation_names(keyword.value, names)
    return names


def async_function_arg_names(path: Path, function_name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            return tuple(arg.arg for arg in node.args.args)
    msg = f"async function {function_name!r} not found in {path}"
    raise AssertionError(msg)
