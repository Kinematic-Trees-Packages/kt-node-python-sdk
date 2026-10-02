"""Run manifest-driven typed Get/Set through the real HTTP runtime and C ABI."""

from __future__ import annotations

import argparse
import http.client
import json
import socket
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from kt.messages import codec_for
from ktnode import Context, Get, NextStep, Node, Runtime, Set


def reserve_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def write_fixture(directory: Path, port: int) -> tuple[str, str]:
    package = directory / "node.package.json"
    runtime = directory / "runtime.json"
    package.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "metadata": {"name": "python-typed-channel-conformance"},
                "dataflow": {
                    "inputs": [{"name": "example_input", "datatype": "kt/speech/string_sample"}],
                    "outputs": [{"name": "example_output", "datatype": "kt/speech/string_sample"}],
                },
            }
        ),
        encoding="utf-8",
    )
    runtime.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "id": "python-typed-channel-conformance",
                "package": "node.package.json",
                "execution": {"algorithm": {"mode": "event_driven"}},
                "transport": {
                    "http": {
                        "bind": {"interface": "127.0.0.1", "port": port},
                        "routes": {
                            "example_input": {"mode": "server", "path": "/in", "method": "POST"},
                            "example_output": {"mode": "server", "path": "/out", "method": "GET"},
                        },
                    }
                },
                "channelDefaults": [
                    {
                        "match": {"direction": direction, "transport": "http"},
                        "buffer": {"capacity": 2, "treatment": "drop_old"},
                    }
                    for direction in ("input", "output")
                ],
            }
        ),
        encoding="utf-8",
    )
    return str(package), str(runtime)


@dataclass
class TypedRelay(Node):
    observed: list[str] = field(default_factory=list)
    published: threading.Event = field(default_factory=threading.Event)

    def step(self, ctx: Context) -> NextStep:
        value = Get(ctx, "example_input")
        if value is None:
            return NextStep.CONTINUE
        assert isinstance(value, str)
        self.observed.append(value)
        Set(ctx, "example_output", value)
        self.published.set()
        return NextStep.CONTINUE


def request(port: int, method: str, path: str, body: bytes = b"") -> tuple[int, bytes]:
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


def post_without_waiting(port: int, body: bytes) -> socket.socket:
    deadline = time.monotonic() + 10
    while True:
        try:
            stream = socket.create_connection(("127.0.0.1", port), timeout=2)
            request_bytes = (
                f"POST /in HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode() + body
            stream.sendall(request_bytes)
            return stream
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.02)


def run(library: str) -> dict[str, object]:
    text = "typed Ω passthrough"
    codec = codec_for("kt/speech/string_sample")
    encoded = bytes(codec.encode(text))
    with tempfile.TemporaryDirectory(prefix="kt-python-typed-") as temporary:
        port = reserve_port()
        package, runtime_path = write_fixture(Path(temporary), port)
        relay = TypedRelay()
        runtime = Runtime(package, runtime_path, relay, library_path=library)
        failure: list[BaseException] = []

        def run_runtime() -> None:
            try:
                runtime.run()
            except BaseException as error:
                failure.append(error)

        runner = threading.Thread(target=run_runtime)
        runner.start()
        stream: socket.socket | None = None
        try:
            stream = post_without_waiting(port, encoded)
            assert relay.published.wait(10), "typed callback did not publish"
            deadline = time.monotonic() + 10
            output = b""
            while time.monotonic() < deadline:
                status, output = request(port, "GET", "/out")
                if status < 300 and output == encoded:
                    break
                time.sleep(0.02)
            assert output == encoded
            assert codec.decode(output) == text
            assert relay.observed == [text]
            runtime.request_close()
            runner.join(10)
            assert not runner.is_alive()
            assert not failure, failure
        finally:
            if stream is not None:
                stream.close()
            if runner.is_alive():
                runtime.request_close()
                runner.join(5)
            runtime.close()
    return {"datatype": "kt/speech/string_sample", "value": text, "payloadBytes": len(encoded)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    args = parser.parse_args()
    print("KT_TYPED_CHANNEL_CONFORMANCE=" + json.dumps(run(args.library), sort_keys=True))


if __name__ == "__main__":
    main()
