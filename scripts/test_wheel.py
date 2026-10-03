#!/usr/bin/env python3
"""Build and prove the public SDK wheel in a clean Python environment."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = pathlib.Path(__file__).with_name("build_wheel.py")
SPEC = importlib.util.spec_from_file_location("build_wheel", SCRIPT)
assert SPEC and SPEC.loader
BUILD_WHEEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_WHEEL)


class WheelTests(unittest.TestCase):
    def test_wheel_installs_and_imports_without_source_path(self) -> None:
        root = pathlib.Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temporary = pathlib.Path(directory)
            wheel = BUILD_WHEEL.build_wheel(root, temporary / "wheelhouse")
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
            self.assertNotIn("ktnode/vision.py", names)
            self.assertFalse(any(name.startswith("ktnode/generated/") for name in names))
            environment = temporary / "venv"
            subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
            python = environment / "bin" / "python"
            dependencies = []
            messages_wheel = os.environ.get("KT_MESSAGES_WHEEL")
            flatbuffers_wheel = os.environ.get("KT_FLATBUFFERS_WHEEL")
            if bool(messages_wheel) != bool(flatbuffers_wheel):
                self.fail("KT_MESSAGES_WHEEL and KT_FLATBUFFERS_WHEEL must be provided together")
            if flatbuffers_wheel and messages_wheel:
                dependencies.extend((flatbuffers_wheel, messages_wheel))
            subprocess.run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-index",
                    "--no-deps",
                    *dependencies,
                    str(wheel),
                ],
                check=True,
            )
            probe = subprocess.run(
                [
                    str(python),
                    "-c",
                    (
                        "import importlib.metadata, ktnode, pathlib; "
                        "assert importlib.metadata.version('kt-python-sdk') == '0.2.0'; "
                        "assert 'site-packages' in pathlib.Path(ktnode.__file__).as_posix(); "
                        + (
                            "from kt.messages import codec_for; "
                            "assert codec_for('kt/speech/string_sample').decode("
                            "codec_for('kt/speech/string_sample').encode('clean-wheel')) == 'clean-wheel'; "
                            "assert callable(ktnode.Get) and callable(ktnode.Set); "
                            if messages_wheel
                            else ""
                        )
                        +
                        "print(ktnode.__file__)"
                    ),
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("site-packages/ktnode/__init__.py", probe.stdout)


if __name__ == "__main__":
    unittest.main()
