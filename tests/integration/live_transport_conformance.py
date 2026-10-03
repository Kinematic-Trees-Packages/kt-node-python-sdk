"""Run one transport-neutral Python relay over HTTP or KT SHM."""

from __future__ import annotations

import argparse
import http.client
import json
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ktnode import Capability, Context, KtError, NextStep, Node, ReadMode, Runtime


def _reserve_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _write_fixture(directory: Path, transport: str, token: str) -> tuple[str, str, int | None]:
    package = directory / "package.ktm.json"
    runtime = directory / "runtime.json"
    package.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "metadata": {"name": "python-transport-conformance"},
                "dataflow": {
                    "inputs": [{"name": "in", "datatype": "kt/common/blob_sample"}],
                    "outputs": [{"name": "out", "datatype": "kt/common/blob_sample"}],
                },
            }
        ),
        encoding="utf-8",
    )
    port: int | None = None
    if transport == "http":
        port = _reserve_port()
        transport_config = {
            "http": {
                "bind": {"interface": "127.0.0.1", "port": port},
                "routes": {
                    "in": {"mode": "server", "path": "/in", "method": "POST"},
                    "out": {"mode": "server", "path": "/out", "method": "GET"},
                },
            }
        }
        selected = "http"
    else:
        transport_config = {
            "kt_shm": {
                "routes": {
                    "in": {
                        "mode": "client",
                        "service": f"kt/python/{token}/in",
                        "subscriberBufferSize": 2,
                        "maxSampleSize": 4 * 1024 * 1024,
                        "pollIntervalMs": 5,
                    },
                    "out": {
                        "mode": "server",
                        "service": f"kt/python/{token}/out",
                        "subscriberBufferSize": 2,
                        "maxSampleSize": 4 * 1024 * 1024,
                        "pollIntervalMs": 5,
                    },
                }
            }
        }
        selected = "kt_shm"
    runtime.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "id": "python-transport-conformance",
                "package": "package.ktm.json",
                "execution": {"algorithm": {"mode": "event_driven"}},
                "transport": transport_config,
                "channelDefaults": [
                    {"match": {"direction": direction, "transport": selected}, "buffer": {"capacity": 2, "treatment": "drop_old"}}
                    for direction in ("input", "output")
                ],
            }
        ),
        encoding="utf-8",
    )
    return str(package), str(runtime), port


@dataclass
class RelayProbe(Node):
    expected: bytes
    observed: list[bytes] = field(default_factory=list)
    published: threading.Event = field(default_factory=threading.Event)

    def step(self, ctx: Context) -> NextStep:
        messages = ctx.get("in", ReadMode.ALL_AVAILABLE)
        if not messages:
            return NextStep.CONTINUE
        for message in messages:
            self.observed.append(message.payload)
            ctx.set("out", message.payload)
            if message.payload == self.expected:
                self.published.set()
        return NextStep.CONTINUE


def _http_request(port: int, method: str, path: str, body: bytes = b"") -> tuple[int, bytes]:
    deadline = time.monotonic() + 10
    while True:
        try:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            connection.request(method, path, body=body)
            response = connection.getresponse()
            payload = response.read()
            connection.close()
            return response.status, payload
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def _http_post_without_waiting(port: int, body: bytes) -> socket.socket:
    deadline = time.monotonic() + 10
    while True:
        try:
            stream = socket.create_connection(("127.0.0.1", port), timeout=2)
            request = (f"POST /in HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
            stream.sendall(request)
            return stream
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def _run_runtime(runtime: Runtime, failure: list[BaseException]) -> None:
    try:
        runtime.run()
    except BaseException as error:
        failure.append(error)


def run_http(library: str, payload: bytes) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="kt-python-http-") as temporary:
        package, runtime_path, port = _write_fixture(Path(temporary), "http", "unused")
        assert port is not None
        probe = RelayProbe(payload)
        runtime = Runtime(package, runtime_path, probe, library_path=library)
        runtime.require_capability(Capability.HTTP)
        failure: list[BaseException] = []
        runner = threading.Thread(target=_run_runtime, args=(runtime, failure))
        runner.start()
        try:
            post_stream = _http_post_without_waiting(port, payload)
            assert probe.published.wait(10)
            deadline = time.monotonic() + 10
            output = b""
            while time.monotonic() < deadline:
                status, output = _http_request(port, "GET", "/out")
                if status < 300 and output == payload:
                    break
                time.sleep(0.02)
            assert output == payload
            runtime.request_close()
            runner.join(10)
            assert not runner.is_alive()
            assert not failure, failure
            assert probe.observed[-1] == payload
            post_stream.close()
        finally:
            if runner.is_alive():
                runtime.request_close()
                runner.join(5)
            runtime.close()
    return {"transport": "http", "payload_bytes": len(payload), "recovery": "port-released-on-close"}


def run_shm(library: str, peer: str, payload: bytes) -> dict[str, object]:
    token = f"{time.time_ns()}-{socket.gethostname()}"
    with tempfile.TemporaryDirectory(prefix="kt-python-shm-") as temporary:
        package, runtime_path, _ = _write_fixture(Path(temporary), "kt_shm", token)
        probe = RelayProbe(payload)
        runtime = Runtime(package, runtime_path, probe, library_path=library)
        runtime.require_capability(Capability.KT_SHM)
        failure: list[BaseException] = []
        runner = threading.Thread(target=_run_runtime, args=(runtime, failure))
        runner.start()
        try:
            completed = subprocess.run(
                [peer, f"kt/python/{token}/in", f"kt/python/{token}/out", payload.decode("ascii")],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            runtime.request_close()
            runner.join(10)
            assert not runner.is_alive()
            assert not failure, failure
            assert probe.observed[-1] == payload
            marker = next(line for line in completed.stdout.splitlines() if line.startswith("KT_SHM_PEER="))
            peer_result = json.loads(marker.removeprefix("KT_SHM_PEER="))
        finally:
            if runner.is_alive():
                runtime.request_close()
                runner.join(5)
            runtime.close()
    return {"transport": "kt_shm", **peer_result, "recovery": "late-peer-discovery"}


def run_invalid_config(library: str, transport: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="kt-python-invalid-") as temporary:
        root = Path(temporary)
        package, runtime_path, _ = _write_fixture(root, transport, "invalid-token")
        runtime_json = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
        if transport == "http":
            runtime_json["transport"]["http"]["routes"]["in"]["method"] = "GET"
            expected = "must use POST, PUT, or PATCH"
        else:
            runtime_json["transport"]["kt_shm"]["routes"]["in"]["service"] = "bad\0service"
            expected = "invalid service"
        Path(runtime_path).write_text(json.dumps(runtime_json), encoding="utf-8")
        try:
            Runtime(package, runtime_path, RelayProbe(b"unused"), library_path=library)
        except KtError as error:
            message = str(error)
            assert expected in message, message
            return {"transport": transport, "error": message}
        raise AssertionError(f"invalid {transport} configuration was accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    parser.add_argument("--transport", choices=("http", "kt_shm"), required=True)
    parser.add_argument("--peer")
    parser.add_argument("--negative", action="store_true")
    args = parser.parse_args()
    payload = b"vision-scalar-fixture"
    if args.negative:
        result = run_invalid_config(args.library, args.transport)
    else:
        result = (
            run_http(args.library, payload)
            if args.transport == "http"
            else run_shm(args.library, args.peer or parser.error("--peer is required for kt_shm"), payload)
        )
    print("KT_TRANSPORT_CONFORMANCE=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
