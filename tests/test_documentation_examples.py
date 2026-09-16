from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from types import ModuleType

from ktnode import NextStep, Node


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_documented_python_sources_parse_and_import() -> None:
    paths = sorted((ROOT / "examples").rglob("*.py"))
    assert paths
    for path in paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        _load(path, f"docs_{path.stem}")


def test_minimal_process_uses_public_node_contract() -> None:
    module = _load(ROOT / "examples/minimal_process.py", "minimal_process")
    assert issubclass(module.EchoNode, Node)
    assert module.NextStep.CONTINUE is NextStep.CONTINUE


def test_all_python_markdown_fences_compile() -> None:
    fence = re.compile(r"```python\n(.*?)```", re.DOTALL)
    pages = sorted((ROOT / "docs/site").rglob("*.md"))
    snippets = [(page, code) for page in pages for code in fence.findall(page.read_text(encoding="utf-8"))]
    assert snippets
    for page, code in snippets:
        compile(code, f"{page}:python-fence", "exec")
