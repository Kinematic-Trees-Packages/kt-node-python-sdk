from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/minimum_process_contract/v1"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def test_contract_keeps_boundaries_distinct() -> None:
    package = load("package.ktm.json")
    runtime = load("runtime.json")
    assert package["schemaVersion"] == "3"
    assert runtime["schemaVersion"] == "4"
    assert "dataflow" in package and "config" in package
    assert "dependencies" not in runtime and "dataflow" not in runtime
    assert runtime["package"] == "./package.ktm.json"
    assert runtime["id"] != package["metadata"]["name"]
    assert not list(FIXTURE.rglob("node.package.json"))


def test_contract_freezes_typed_semantics_routes_and_defaults() -> None:
    package = load("package.ktm.json")
    runtime = load("runtime.json")
    inputs = package["dataflow"]["inputs"]
    outputs = package["dataflow"]["outputs"]
    assert [(item["name"], item["datatype"]) for item in inputs] == [("value", "kt/common/int64_value")]
    assert inputs[0]["required"] is True
    assert [(item["name"], item["datatype"]) for item in outputs] == [("incremented", "kt/common/int64_value")]
    assert package["config"]["properties"]["increment"]["default"] == 1
    assert package["config"]["required"] == ["increment"]
    assert runtime["config"] == {"increment": 1}
    routes = runtime["transport"]["http"]["routes"]
    assert set(routes) == {"value", "incremented"}
    assert routes["value"]["method"] == "POST"
    assert routes["incremented"]["method"] == "GET"
    assert runtime["channelDefaults"][0]["buffer"]["capacity"] == 1


def test_lifecycle_declares_direct_process_entrypoint() -> None:
    package = load("package.ktm.json")
    run = package["runEnvironments"][0]["recipes"][0]
    assert run["action"] == "run"
    assert run["command"] == {
        "program": "python3",
        "args": ["-m", "minimum_contract", "--package", "package.ktm.json", "--runtime", "runtime.json"],
    }


def test_fixture_versions_required_validation_failures() -> None:
    errors = load("expected-errors.json")
    assert errors["schemaVersion"] == "minimum-process-errors.v1"
    assert [failure["id"] for failure in errors["failures"]] == [
        "dependency", "required-route", "unknown-route", "datatype", "duplicate-channel",
        "increment-config", "payload", "multiplicity", "overflow",
    ]
    assert {failure["owner"] for failure in errors["failures"]} == {"lifecycle", "package", "cross-file", "process"}


def test_contract_records_metadata_and_error_decisions() -> None:
    text = (ROOT / "docs/site/reference/minimum-process-contract.md").read_text(encoding="utf-8")
    assert "Proposal, not current platform fact" in text
    assert "source_id" in text and "remote_time_ns" in text
    assert "Multiple sources" in text
    assert "malformed `Int64Value` bytes" in text
