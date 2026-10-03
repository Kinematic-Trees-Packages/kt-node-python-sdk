"""Clean-environment probe for the frozen native ABI artifact."""

from __future__ import annotations

import ctypes
import sys

from ktnode import Capability, ClosedResourceError, Runtime, abi


def main(library: str, package_path: str, runtime_path: str) -> None:
    runtime = Runtime(package_path, runtime_path, __import__("ktnode").Node(), library_path=library)
    assert runtime.info.abi_major == 1
    assert runtime.info.abi_minor >= 2
    assert runtime.info.creation_api == 2
    assert runtime.info.build_id
    assert runtime.info.capabilities & Capability.HTTP
    runtime.close()
    assert runtime.closed
    runtime.close()
    try:
        runtime.request_close()
    except ClosedResourceError:
        pass
    else:
        raise AssertionError("closed runtime accepted request_close")

    # Prove exported configuration accessors are bound with the frozen types.
    lib = abi.load_library(library)
    assert lib.kt_context_config_revision.argtypes == [ctypes.POINTER(abi.KtAlgorithmContext)]
    assert lib.kt_runtime_create_v2.argtypes[0]._type_ is abi.KtRuntimeOptionsV2


if __name__ == "__main__":
    main(*sys.argv[1:])
