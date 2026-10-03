from __future__ import annotations

import pathlib
import zipfile

from scripts.build_wheel import build_wheel


ROOT = pathlib.Path(__file__).resolve().parents[2]
PUBLIC_WHEEL_FILES = {
    "ktnode/__init__.py",
    "ktnode/abi.py",
    "ktnode/channels.py",
    "ktnode/errors.py",
    "ktnode/py.typed",
    "ktnode/runtime.py",
    "ktnode/vision.py",
}


def test_repository_has_one_template_authority() -> None:
    assert not (ROOT / "boilerplate").exists()
    assert (ROOT / "template-package" / "boilerplate" / "ktm-template.json").is_file()


def test_coverage_runner_excludes_host_only_abi_contract() -> None:
    coverage_script = (ROOT / "scripts" / "coverage.sh").read_text(encoding="utf-8")
    assert "--ignore=tests/contract/test_contract_matrix.py" in coverage_script


def test_wheel_contains_only_public_sdk_package(tmp_path: pathlib.Path) -> None:
    wheel = build_wheel(ROOT, tmp_path)
    with zipfile.ZipFile(wheel) as archive:
        payload = {
            name
            for name in archive.namelist()
            if not name.startswith("kt_python_sdk-0.2.0.dist-info/")
        }
    assert payload == PUBLIC_WHEEL_FILES
