import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = "honest_starter"


class TemplateFailureStatusTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        self.project = self.root / "project"
        self.composed = self.root / "composed"
        self.include = self.root / "include"
        self.library = self.root / "library"
        shutil.copytree(ROOT / "template-package" / "boilerplate", self.project)
        module_template = self.project / "src" / "{{KTM_CREATE_MODULE_NAME}}"
        module_template.rename(module_template.with_name(MODULE))

        for path in list(self.project.rglob("*")):
            if not path.is_file():
                continue
            path.write_text(path.read_text().replace("{{KTM_CREATE_MODULE_NAME}}", MODULE))
            if path.name.endswith(".template"):
                path.rename(path.with_name(path.name.removesuffix(".template")))

        messages = self.composed / "kt" / "messages"
        messages.mkdir(parents=True)
        (self.composed / "kt" / "__init__.py").write_text("")
        names = [
            "codec_for",
            "registered_datatypes",
            "string_sample",
            "vision_sample",
            *(f"schema_{index:02d}" for index in range(22)),
        ]
        (messages / "__init__.py").write_text(
            f"__all__ = {names!r}\n" + "\n".join(f"{name} = object()" for name in names) + "\n"
        )
        (self.composed / "ktnode.py").write_text(
            "class Context: pass\n"
            "class Node: pass\n"
            "class Runtime: pass\n"
            "class ConfigUpdate:\n"
            "    def __init__(self, *args): pass\n"
            "class ConfigUpdateResult: pass\n"
            "class NextStep:\n"
            "    CONTINUE = object()\n"
            "    STOP = object()\n"
            "def Get(*args, **kwargs): return None\n"
            "def Set(*args, **kwargs): return None\n"
        )
        self.include.mkdir()
        self.library.mkdir()
        (self.include / "kt_node.h").write_text("/* fixture */\n")
        (self.library / "libkt_node.so").write_bytes(b"")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_script(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "CPATH": str(self.include),
                "LIBRARY_PATH": str(self.library),
                "PYTHONPATH": str(self.composed),
            }
        )
        return subprocess.run(
            ["bash", "scripts/test.sh"],
            cwd=self.project,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_baseline_runs_real_unittest_and_preserves_composed_path(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Running generated unittest suite", result.stdout)
        self.assertIn("Ran 2 tests", result.stdout)
        self.assertIn("OK", result.stdout)
        self.assertIn("kt-messages wildcard import passed", result.stdout)

    def test_assertion_failure_is_nonzero_with_original_diagnostic(self) -> None:
        test_file = self.project / "tests" / "test_smoke.py"
        test_file.write_text(
            test_file.read_text().replace(
                'self.assertEqual(Process.__mro__[1].__name__, "Node")',
                'self.fail("KIN-14 deliberate assertion failure")',
            )
        )
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("KIN-14 deliberate assertion failure", result.stdout)

    def test_import_failure_is_nonzero_with_original_diagnostic(self) -> None:
        test_file = self.project / "tests" / "test_smoke.py"
        test_file.write_text("import deliberately_missing_kin14_dependency\n" + test_file.read_text())
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("ModuleNotFoundError", result.stdout)
        self.assertIn("deliberately_missing_kin14_dependency", result.stdout)

    def test_outer_ktm_mutation_verifier_rejects_and_restores_failures(self) -> None:
        fake_ktm = self.root / "ktm"
        fake_ktm.write_text("#!/bin/sh\nshift\nexec bash scripts/test.sh\n")
        fake_ktm.chmod(0o755)
        original_test = (self.project / "tests" / "test_smoke.py").read_bytes()
        logs = self.root / "mutation-logs"
        environment = os.environ.copy()
        environment.update(
            {
                "CPATH": str(self.include),
                "LIBRARY_PATH": str(self.library),
                "PYTHONPATH": str(self.composed),
            }
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "test_generated_template_failures.py"),
                "--project",
                str(self.project),
                "--home",
                str(self.root / "home"),
                "--platform",
                "linux_20",
                "--log-dir",
                str(logs),
                "--ktm",
                str(fake_ktm),
            ],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.project / "tests" / "test_smoke.py").read_bytes(), original_test)
        self.assertEqual(len(list(logs.glob("*.log"))), 5)

    def test_packaged_boilerplate_is_the_only_template_authority(self) -> None:
        self.assertTrue((ROOT / "template-package" / "boilerplate" / "ktm-template.json").is_file())
        self.assertFalse((ROOT / "boilerplate").exists())

    def test_build_outputs_runtime_manifests_and_editable_source(self) -> None:
        output = self.root / "build-output"
        result = subprocess.run(
            ["bash", "scripts/build.sh"],
            cwd=self.project,
            env={**os.environ, "KTM_BUILD_OUTPUT": str(output)},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue((output / "runtime" / "src" / MODULE / "process.py").is_file())
        self.assertTrue((output / "runtime" / "src" / MODULE / "__main__.py").is_file())
        self.assertTrue((output / "runtime" / "runtime" / "node.package.json").is_file())
        self.assertTrue((output / "runtime" / "runtime" / "runtime.json").is_file())
        self.assertTrue((output / "source" / "tests" / "test_smoke.py").is_file())


if __name__ == "__main__":
    unittest.main()
