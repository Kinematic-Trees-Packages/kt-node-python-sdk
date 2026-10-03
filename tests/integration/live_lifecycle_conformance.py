"""Real-library lifecycle, ownership, error, and concurrency conformance.

This is intentionally a standalone acceptance fixture rather than a mock-based
unit test. It creates valid package/runtime inputs, loads libkt_node through the
public Python SDK, and exercises every documented terminal path.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import resource
import tempfile
import threading
import time
import weakref
from dataclasses import dataclass, field
from pathlib import Path

from ktnode import ClosedResourceError, Context, KtError, NextStep, Node, Runtime


@dataclass
class ProbeNode(Node):
    setup_result: NextStep = NextStep.CONTINUE
    step_results: list[NextStep] = field(default_factory=lambda: [NextStep.STOP])
    close_result: NextStep = NextStep.STOP
    raise_in: str | None = None
    request_close_in: str | None = None
    block_step: threading.Event | None = None
    release_step: threading.Event | None = None
    calls: list[str] = field(default_factory=list)
    contexts: list[Context] = field(default_factory=list)
    callback_threads: list[int] = field(default_factory=list)
    callback_active: bool = False
    overlap_detected: bool = False
    wrong_thread_error: BaseException | None = None

    def _enter(self, phase: str, ctx: Context) -> None:
        if self.callback_active:
            self.overlap_detected = True
        self.callback_active = True
        self.calls.append(phase)
        self.contexts.append(ctx)
        self.callback_threads.append(threading.get_ident())
        wrong_thread_errors: list[BaseException] = []

        def use_context_from_wrong_thread() -> None:
            try:
                ctx.is_closing()
            except BaseException as error:
                wrong_thread_errors.append(error)

        wrong_thread = threading.Thread(target=use_context_from_wrong_thread)
        wrong_thread.start()
        wrong_thread.join(5)
        if wrong_thread.is_alive():
            raise RuntimeError("wrong-thread context probe did not terminate")
        if wrong_thread_errors:
            self.wrong_thread_error = wrong_thread_errors[0]
        else:
            raise RuntimeError("wrong-thread callback context use unexpectedly succeeded")
        if self.raise_in == phase:
            raise RuntimeError(f"intentional {phase} exception")

    def _leave(self) -> None:
        self.callback_active = False

    def setup(self, ctx):
        try:
            self._enter("setup", ctx)
            if self.request_close_in == "setup":
                ctx.request_close()
            return self.setup_result
        finally:
            self._leave()

    def step(self, ctx):
        try:
            self._enter("step", ctx)
            if self.block_step is not None:
                self.block_step.set()
                assert self.release_step is not None
                if not self.release_step.wait(5):
                    raise RuntimeError("step release timeout")
            if self.request_close_in == "step":
                ctx.request_close()
            return self.step_results.pop(0) if self.step_results else NextStep.STOP
        finally:
            self._leave()

    def close(self, ctx):
        try:
            self._enter("close", ctx)
            return self.close_result
        finally:
            self._leave()


def _write_fixture(directory: Path) -> tuple[str, str]:
    package = directory / "package.ktm.json"
    runtime = directory / "runtime.json"
    package.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "metadata": {"name": "python-lifecycle-conformance"},
                "dataflow": {
                    "inputs": [{"name": "in", "datatype": "kt/common/int64_value"}],
                    "outputs": [],
                },
            }
        ),
        encoding="utf-8",
    )
    runtime.write_text(
        json.dumps(
            {
                "schemaVersion": "4",
                "id": "python-lifecycle-conformance",
                "package": "package.ktm.json",
                "execution": {"algorithm": {"mode": "fixed_rate", "frequencyHz": 1000.0}},
                "transport": {
                    "http": {
                        "bind": {"interface": "127.0.0.1", "port": 0},
                        "routes": {"in": {"mode": "server", "path": "/in", "method": "POST"}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return str(package), str(runtime)


def _run(library: str, package: str, runtime: str, node: ProbeNode) -> Runtime:
    handle = Runtime(package, runtime, node, library_path=library)
    handle.run()
    return handle


def _expect_callback_error(library: str, package: str, runtime: str, node: ProbeNode, detail: str) -> None:
    handle = Runtime(package, runtime, node, library_path=library)
    try:
        try:
            handle.run()
        except KtError as error:
            assert detail in str(error), str(error)
        else:
            raise AssertionError("callback failure unexpectedly succeeded")
    finally:
        handle.close()


def lifecycle_matrix(library: str, package: str, runtime: str) -> None:
    missing = str(Path(package).with_name("missing-package.ktm.json"))
    partial = ProbeNode()
    partial_ref = weakref.ref(partial)
    try:
        Runtime(missing, runtime, partial, library_path=library)
    except KtError:
        pass
    else:
        raise AssertionError("partial initialization unexpectedly succeeded")
    del partial
    gc.collect()
    assert partial_ref() is None, "failed initialization retained callback owner"

    normal = ProbeNode(step_results=[NextStep.STOP])
    handle = _run(library, package, runtime, normal)
    assert normal.calls == ["setup", "step", "close"], normal.calls
    handle.close()
    handle.close()
    try:
        handle.run()
    except ClosedResourceError:
        pass
    else:
        raise AssertionError("closed runtime accepted run")

    preclosed = ProbeNode()
    handle = Runtime(package, runtime, preclosed, library_path=library)
    handle.request_close()
    handle.run()
    assert preclosed.calls == ["setup", "close"], preclosed.calls
    handle.close()

    runtime_close = ProbeNode(request_close_in="setup")
    handle = _run(library, package, runtime, runtime_close)
    assert runtime_close.calls == ["setup", "close"], runtime_close.calls
    handle.close()

    stop_setup = ProbeNode(setup_result=NextStep.STOP)
    handle = _run(library, package, runtime, stop_setup)
    assert stop_setup.calls == ["setup", "close"], stop_setup.calls
    handle.close()

    recoverable = ProbeNode(step_results=[NextStep.RECOVERABLE, NextStep.STOP])
    handle = _run(library, package, runtime, recoverable)
    assert recoverable.calls == ["setup", "step", "step", "close"], recoverable.calls
    handle.close()

    _expect_callback_error(
        library,
        package,
        runtime,
        ProbeNode(setup_result=NextStep.FATAL),
        "setup callback failed",
    )
    _expect_callback_error(
        library,
        package,
        runtime,
        ProbeNode(step_results=[NextStep.FATAL]),
        "step callback failed",
    )
    # The native scheduler logs close failures after terminal cleanup but does
    # not replace an otherwise successful run result with the close error.
    close_fatal = ProbeNode(close_result=NextStep.FATAL)
    handle = _run(library, package, runtime, close_fatal)
    assert close_fatal.calls == ["setup", "step", "close"]
    handle.close()

    close_exception = ProbeNode(raise_in="close")
    handle = _run(library, package, runtime, close_exception)
    assert close_exception.calls == ["setup", "step", "close"]
    handle.close()

    for phase in ("setup", "step"):
        _expect_callback_error(
            library,
            package,
            runtime,
            ProbeNode(raise_in=phase),
            f"Python node {phase} failed: intentional {phase} exception",
        )


def ownership_and_concurrency(library: str, package: str, runtime: str) -> None:
    node = ProbeNode(step_results=[NextStep.STOP])
    node_ref = weakref.ref(node)
    handle = Runtime(package, runtime, node, library_path=library)
    del node
    gc.collect()
    assert node_ref() is not None, "runtime did not retain callback owner"
    handle.run()
    retained = node_ref()
    assert retained is not None
    for context in retained.contexts:
        try:
            context.is_closing()
        except ClosedResourceError:
            pass
        else:
            raise AssertionError("callback context remained usable after callback")
    handle.close()
    del retained
    del handle
    gc.collect()
    assert node_ref() is None, "runtime retained callback owner after destruction"

    entered = threading.Event()
    release = threading.Event()
    concurrent = ProbeNode(
        step_results=[NextStep.CONTINUE],
        block_step=entered,
        release_step=release,
    )
    handle = Runtime(package, runtime, concurrent, library_path=library)
    run_error: list[BaseException] = []

    def run_runtime() -> None:
        try:
            handle.run()
        except BaseException as error:  # captured and asserted on the parent thread
            run_error.append(error)

    runner = threading.Thread(target=run_runtime, name="python-sdk-runtime")
    runner.start()
    assert entered.wait(5), "step callback did not start"
    try:
        handle.close()
    except KtError as error:
        assert "running" in str(error).lower(), str(error)
    else:
        raise AssertionError("destroy during run unexpectedly succeeded")
    handle.request_close()
    release.set()
    runner.join(10)
    assert not runner.is_alive(), "runtime run thread did not terminate"
    assert not run_error, run_error
    handle.close()
    assert not concurrent.overlap_detected
    assert isinstance(concurrent.wrong_thread_error, KtError)


def stress(library: str, package: str, runtime: str, iterations: int, growth_kib: int) -> None:
    gc.collect()
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for _ in range(iterations):
        node = ProbeNode(step_results=[NextStep.STOP])
        handle = Runtime(package, runtime, node, library_path=library)
        handle.run()
        handle.close()
    gc.collect()
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    growth = max(0, after - before)
    assert growth <= growth_kib, f"RSS grew {growth} KiB (budget {growth_kib} KiB)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--growth-kib", type=int, default=65536)
    args = parser.parse_args()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="kt-python-lifecycle-") as temporary:
        package, runtime = _write_fixture(Path(temporary))
        lifecycle_matrix(args.library, package, runtime)
        ownership_and_concurrency(args.library, package, runtime)
        stress(args.library, package, runtime, args.iterations, args.growth_kib)
    print(
        json.dumps(
            {
                "status": "passed",
                "iterations": args.iterations,
                "growth_budget_kib": args.growth_kib,
                "duration_seconds": round(time.monotonic() - started, 3),
                "pid": os.getpid(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
