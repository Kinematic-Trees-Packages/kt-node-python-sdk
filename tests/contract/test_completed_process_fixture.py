from __future__ import annotations

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "completed_process" / "v1"


def test_completed_process_is_versioned_and_separate_from_public_starter() -> None:
    manifest = json.loads((FIXTURE / "package.ktm.json").read_text(encoding="utf-8"))
    assert manifest["dataflow"]["inputs"][0]["name"] == "text_in"
    assert manifest["dataflow"]["outputs"][0]["name"] == "text_out"
    completed = (FIXTURE / "src" / "passthrough" / "robot.py").read_text(encoding="utf-8")
    starter = (
        ROOT
        / "template-package"
        / "boilerplate"
        / "src"
        / "{{KTM_CREATE_MODULE_NAME}}"
        / "robot.py.template"
    ).read_text(encoding="utf-8")
    assert 'Get(ctx, "text_in")' in completed
    assert 'Set(ctx, "text_out", value)' in completed
    assert 'Get(ctx, "text_in")' not in starter
