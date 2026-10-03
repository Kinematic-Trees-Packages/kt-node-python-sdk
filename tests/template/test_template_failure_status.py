import os
import pathlib
import shutil
import subprocess
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
        self.assertIn("Generated Process imports through the public Python SDK", result.stdout)
        self.assertIn("kt-messages wildcard import passed", result.stdout)

    def test_invalid_process_base_is_nonzero_with_original_diagnostic(self) -> None:
        process_file = self.project / "src" / MODULE / "process.py"
        process_file.write_text(process_file.read_text().replace("class Process(kt.Node):", "class Process(object):"))
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("generated Process must inherit the public SDK Node", result.stdout)

    def test_import_failure_is_nonzero_with_original_diagnostic(self) -> None:
        process_file = self.project / "src" / MODULE / "process.py"
        process_file.write_text("import deliberately_missing_dependency\n" + process_file.read_text())
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("ModuleNotFoundError", result.stdout)
        self.assertIn("deliberately_missing_dependency", result.stdout)

    def test_packaged_boilerplate_is_the_only_template_authority(self) -> None:
        self.assertTrue((ROOT / "template-package" / "boilerplate" / "ktm-template.json").is_file())
        self.assertFalse((ROOT / "boilerplate").exists())

    def test_template_contracts_are_flat_and_single_source(self) -> None:
        self.assertTrue((self.project / "package.ktm.json").is_file())
        self.assertTrue((self.project / "runtime.json").is_file())
        self.assertFalse((self.project / "runtime").exists())
        self.assertFalse(list(self.project.rglob("node.package.json")))

    def test_build_outputs_flat_contracts_and_editable_source(self) -> None:
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
        self.assertTrue((output / "package.ktm.json").is_file())
        self.assertTrue((output / "runtime.json").is_file())
        self.assertTrue((output / "src" / MODULE / "process.py").is_file())
        self.assertTrue((output / "src" / MODULE / "__main__.py").is_file())
        self.assertTrue((output / "development" / "scripts" / "test.sh").is_file())
        self.assertFalse((output / "runtime").exists())
        self.assertFalse(list(output.rglob("node.package.json")))


if __name__ == "__main__":
    unittest.main()
