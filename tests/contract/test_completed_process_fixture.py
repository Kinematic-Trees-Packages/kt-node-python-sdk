from __future__ import annotations

import json
import pathlib
import sys

from ktnode import ConfigUpdate, ConfigUpdateResult, NextStep


ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "completed_process" / "v1"
sys.path.insert(0, str(FIXTURE / "src"))

from passthrough import Robot  # noqa: E402


def test_completed_process_is_versioned_and_separate_from_public_starter() -> None:
    manifest = json.loads((FIXTURE / "package.ktm.json").read_text(encoding="utf-8"))
    node = json.loads((FIXTURE / "runtime" / "node.package.json").read_text(encoding="utf-8"))
    runtime = json.loads((FIXTURE / "runtime" / "runtime.json").read_text(encoding="utf-8"))
    assert manifest["dataflow"]["inputs"][0]["name"] == "example_input"
    assert manifest["dataflow"]["outputs"][0]["name"] == "example_output"
    assert {
        direction: [
            {key: value for key, value in channel.items() if key != "description"}
            for channel in channels
        ]
        for direction, channels in node["dataflow"].items()
    } == manifest["dataflow"]
    assert runtime["id"] == node["metadata"]["name"]
    assert runtime["package"] == "node.package.json"
    completed = (FIXTURE / "src" / "passthrough" / "robot.py").read_text(encoding="utf-8")
    starter = (
        ROOT
        / "template-package"
        / "boilerplate"
        / "src"
        / "{{KTM_CREATE_MODULE_NAME}}"
        / "robot.py.template"
    ).read_text(encoding="utf-8")
    assert 'Get(ctx, "example_input")' in completed
    assert 'Set(ctx, "example_output", value)' in completed
    assert '# value = Get(ctx, "example_input")' in starter
    assert '\n        value = Get(ctx, "example_input")' not in starter


def test_completed_process_implements_all_lifecycle_callbacks() -> None:
    robot = Robot()
    assert robot.setup(None) is NextStep.CONTINUE
    update = ConfigUpdate(
        old_revision=4,
        new_revision=5,
        patch=[{"op": "replace", "path": "/mode", "value": "safe"}],
        old_config={"mode": "fast"},
        new_config={"mode": "safe"},
        changed_paths=["/mode"],
        flags=0,
    )
    assert robot.config_update(None, update) is ConfigUpdateResult.ACCEPT
    assert robot.config_updates == [update]
    assert robot.close(None) is NextStep.STOP
    assert robot.close_count == 1
    assert robot.calls == ["setup", "config_update", "close"]
