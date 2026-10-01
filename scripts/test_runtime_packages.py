"""Contract tests for the SDK's typed runtime package export."""

import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).parents[1]
IMPORT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


def load_manifest(path: pathlib.Path) -> dict:
    payload = path.read_text().replace("{{KTM_CREATE_RUN_ENVIRONMENTS_JSON}}", "[]")
    return json.loads(payload)


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

    def test_datatypes_are_a_direct_package_dependency(self) -> None:
        paths = [
            ROOT / "package.ktm.json",
            ROOT / "boilerplate" / "package.ktm.json.template",
            ROOT / "template-package" / "package.ktm.json",
            ROOT / "template-package" / "boilerplate" / "package.ktm.json.template",
        ]
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                dependencies = load_manifest(path)["dependencies"]["packages"]
                messages = [item for item in dependencies if item["name"] == "kt-messages"]
                self.assertEqual(len(messages), 1)
                self.assertEqual(
                    {key: messages[0][key] for key in ("owner", "name", "version", "classification")},
                    {
                        "owner": "kinematictrees",
                        "name": "kt-messages",
                        "version": "0.1.0",
                        "classification": "data_types",
                    },
                )
                self.assertTrue(messages[0]["environments"])


if __name__ == "__main__":
    unittest.main()
