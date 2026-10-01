#!/usr/bin/env python3
"""Build the SDK wheel into an explicit directory without resolving dependencies."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys


def build_wheel(root: pathlib.Path, output: pathlib.Path) -> pathlib.Path:
    root = root.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=True)
    # Setuptools reuses build/lib between invocations and does not remove files
    # deleted from the source tree. Clear only that generated staging directory
    # so retired modules cannot leak into a release wheel.
    shutil.rmtree(root / "build" / "lib", ignore_errors=True)
    before = {path.resolve() for path in output.glob("*.whl")}
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-deps",
            "--wheel-dir",
            str(output),
            str(root),
        ],
        check=True,
    )
    created = sorted(path.resolve() for path in output.glob("*.whl") if path.resolve() not in before)
    if len(created) != 1:
        raise RuntimeError(f"expected one newly built wheel, found {len(created)}")
    return created[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    wheel = build_wheel(pathlib.Path(__file__).parents[1], args.output)
    print(wheel)


if __name__ == "__main__":
    main()
