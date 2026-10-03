"""Real-runtime Python data-model conformance over the public C ABI."""

from __future__ import annotations

import argparse
import http.client
import json
import resource
import socket
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ktnode import Context, NextStep, Node, ReadMode, Runtime


def _reserve_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _write_fixture(directory: Path, port: int) -> tuple[str, str]:
    package = directory / "package.ktm.json"
    runtime = directory / "runtime.json"
    package.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "metadata": {"name": "python-data-model-conformance"},
                "dataflow": {
                    "inputs": [{"name": "in", "datatype": "kt/common/blob_sample"}],
                    "outputs": [{"name": "out", "datatype": "kt/common/blob_sample"}],
                },
            }
        ),
        encoding="utf-8",
    )
    runtime.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "id": "python-data-model-conformance",
                "package": "package.ktm.json",
                "execution": {"algorithm": {"mode": "event_driven"}},
                "transport": {
                    "http": {
                        "bind": {"interface": "127.0.0.1", "port": port},
                        "routes": {
                            "in": {"mode": "server", "path": "/in", "method": "POST"},
                            "out": {"mode": "server", "path": "/out", "method": "GET"},
                        },
                    }
                },
                "channelDefaults": [
                    {
                        "match": {"direction": "input", "transport": "http"},
                        "buffer": {"capacity": 16, "treatment": "drop_old"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return str(package), str(runtime)


@dataclass
class DataProbe(Node):
    expected: list[bytes]
    output: bytes
    observed: list[bytes] = field(default_factory=list)
    phase: int = 0

    def setup(self, ctx: Context) -> NextStep:
        assert ctx.get("in", ReadMode.ALL_AVAILABLE) == []
        return NextStep.CONTINUE

    def step(self, ctx: Context) -> NextStep:
        messages = ctx.get("in", ReadMode.ONE)
        assert messages
        assert all(message.source_id is None for message in messages)
        assert all(message.remote_time_ns is None for message in messages)
        self.observed.extend(message.payload for message in messages)
        if self.phase == len(self.expected) - 1:
            mutable = bytearray(self.output)
            ctx.set("out", mutable)
            mutable[:] = b"\x55" * len(mutable)
            self.phase += 1
            return NextStep.STOP
        self.phase += 1
        return NextStep.CONTINUE


def _post_without_waiting(port: int, body: bytes) -> socket.socket:
    deadline = time.monotonic() + 5
    while True:
        try:
            stream = socket.create_connection(("127.0.0.1", port), timeout=5)
            request = (f"POST /in HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
            stream.sendall(request)
            return stream
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def _request(port: int, method: str, path: str, body: bytes = b"") -> tuple[int, bytes]:
    deadline = time.monotonic() + 5
    while True:
        try:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request(method, path, body=body)
            response = connection.getresponse()
            payload = response.read()
            connection.close()
            return response.status, payload
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def run_fixture(library: str) -> dict[str, object]:
    rss_before_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    scalar = (-(2**63) + 1).to_bytes(8, "little", signed=True)
    structured = json.dumps(
        {"datatype": "kt/state/example", "unicode": "robot-α", "nested": {"ok": True}},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    empty = b""
    malformed_vision = b"VSM1\x00\xffnot-a-schema\x00"
    large = bytes(range(256)) * 4
    composite = b"".join(len(payload).to_bytes(8, "little") + payload for payload in (large, scalar, empty, structured, malformed_vision))
    groups = [[composite]]
    expected = [composite]
    output = b"\x00\xffpython-output\x00"
    with tempfile.TemporaryDirectory(prefix="kt-python-data-") as temporary:
        port = _reserve_port()
        package, runtime_path = _write_fixture(Path(temporary), port)
        probe = DataProbe(expected=expected, output=output)
        runtime = Runtime(package, runtime_path, probe, library_path=library)
        assert runtime.info.creation_api == 2
        failure: list[BaseException] = []

        def run_runtime() -> None:
            try:
                runtime.run()
            except BaseException as error:
                failure.append(error)

        runner = threading.Thread(target=run_runtime)
        runner.start()
        try:
            streams: list[socket.socket] = []
            for index, group in enumerate(groups):
                streams.append(_post_without_waiting(port, group[0]))
                deadline = time.monotonic() + 5
                while probe.phase <= index and time.monotonic() < deadline:
                    time.sleep(0.005)
                assert probe.phase > index, f"runtime did not consume phase {index}"
            runner.join(5)
            assert not runner.is_alive()
            assert not failure, failure
            assert probe.observed == expected, [len(value) for value in probe.observed]
            for stream in streams:
                stream.close()
        finally:
            if runner.is_alive():
                runtime.request_close()
                runner.join(5)
            runtime.close()
    rss_growth_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - rss_before_kib
    assert rss_growth_kib <= 64 * 1024, rss_growth_kib
    return {
        "live_read_mode": "one",
        "abi_read_modes": ["one", "count", "all_available"],
        "fixture_classes": ["large", "scalar", "empty", "structured", "malformed-vision"],
        "payload_count": len(expected),
        "payload_bytes": sum(len(payload) for payload in expected),
        "write_copy_input_bytes": len(output),
        "source_ids": "absent-single-source",
        "remote_timestamps": "absent-http",
        "rss_growth_kib": rss_growth_kib,
        "rss_limit_kib": 64 * 1024,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    args = parser.parse_args()
    print("KT_DATA_CONFORMANCE=" + json.dumps(run_fixture(args.library), sort_keys=True))


if __name__ == "__main__":
    main()
