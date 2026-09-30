"""Contract tests for the SDK's typed runtime package export."""

import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).parents[1]
IMPORT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


class RuntimePackageContractTests(unittest.TestCase):
    def test_all_environments_export_the_same_python_wheel(self) -> None:
        manifest = json.loads((ROOT / "package.ktm.json").read_text())
        expected = {
            "ecosystem": "python",
            "name": "kt-node-python-sdk",
            "version": manifest["metadata"]["version"],
            "artifact": {
                "format": "wheel",
                "path": "python-dist/kt_node_python_sdk-0.2.0-py3-none-any.whl",
            },
            "python": {"importNames": ["ktnode"], "requiresPython": ">=3.9"},
        }
        environments = manifest["runEnvironments"]
        self.assertGreater(len(environments), 0)
        for environment in environments:
            with self.subTest(environment=environment["name"]):
                packages = environment["runtimeExports"]["runtimePackages"]
                self.assertEqual(packages, [expected])
                self.assertTrue(packages[0]["artifact"]["path"].endswith(".whl"))
                self.assertTrue(all(IMPORT_NAME.fullmatch(name) for name in packages[0]["python"]["importNames"]))

    def test_legacy_python_distribution_export_is_absent(self) -> None:
        manifest = json.loads((ROOT / "package.ktm.json").read_text())
        for environment in manifest["runEnvironments"]:
            self.assertNotIn("pythonDistributions", environment["runtimeExports"])


if __name__ == "__main__":
    unittest.main()
