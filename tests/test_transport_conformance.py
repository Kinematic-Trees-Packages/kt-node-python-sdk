from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from ktnode import Capability, UnsupportedCapabilityError
from live_transport_conformance import RelayProbe, _write_fixture


def test_same_relay_class_is_used_for_every_required_transport() -> None:
    http = RelayProbe(b"payload")
    shm = RelayProbe(b"payload")
    assert type(http) is type(shm) is RelayProbe


@pytest.mark.parametrize("transport", ["http", "kt_shm"])
def test_runtime_selection_stays_in_configuration(tmp_path: Path, transport: str) -> None:
    package, runtime_path, port = _write_fixture(tmp_path, transport, "fixture-token")
    package_json = json.loads(Path(package).read_text(encoding="utf-8"))
    runtime_json = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
    assert [item["name"] for item in package_json["dataflow"]["inputs"]] == ["in"]
    assert [item["name"] for item in package_json["dataflow"]["outputs"]] == ["out"]
    assert list(runtime_json["transport"]) == [transport]
    assert (port is not None) is (transport == "http")
    source = inspect.getsource(RelayProbe.step)
    assert "http" not in source
    assert "kt_shm" not in source


def test_shm_fixture_freezes_backpressure_limits(tmp_path: Path) -> None:
    _, runtime_path, _ = _write_fixture(tmp_path, "kt_shm", "fixture-token")
    runtime_json = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
    routes = runtime_json["transport"]["kt_shm"]["routes"]
    assert {route["subscriberBufferSize"] for route in routes.values()} == {2}
    assert {route["maxSampleSize"] for route in routes.values()} == {4 * 1024 * 1024}


def test_invalid_transport_configs_are_explicit(tmp_path: Path) -> None:
    (tmp_path / "http").mkdir()
    _, http_path, _ = _write_fixture(tmp_path / "http", "http", "unused")
    http = json.loads(Path(http_path).read_text(encoding="utf-8"))
    http["transport"]["http"]["routes"]["in"]["method"] = "GET"
    assert http["transport"]["http"]["routes"]["in"]["method"] == "GET"

    (tmp_path / "shm").mkdir()
    _, shm_path, _ = _write_fixture(tmp_path / "shm", "kt_shm", "fixture-token")
    shm = json.loads(Path(shm_path).read_text(encoding="utf-8"))
    shm["transport"]["kt_shm"]["routes"]["in"]["service"] = "bad\0service"
    assert "\0" in shm["transport"]["kt_shm"]["routes"]["in"]["service"]


def test_missing_transport_capability_is_not_silently_substituted() -> None:
    from ktnode.runtime import Runtime

    class RuntimeStub:
        info = type("Info", (), {"capabilities": Capability.HTTP})()

        def _require_open(self) -> None:
            pass

    with pytest.raises(UnsupportedCapabilityError, match="KT_SHM"):
        Runtime.require_capability(RuntimeStub(), Capability.KT_SHM)  # type: ignore[arg-type]
