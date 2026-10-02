"""Contract tests for the SDK's typed runtime package export."""

import json
import pathlib
import re
import unittest
from typing import Any, cast


ROOT = pathlib.Path(__file__).parents[1]
IMPORT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    payload = path.read_text().replace("{{KTM_CREATE_RUN_ENVIRONMENTS_JSON}}", "[]")
    payload = payload.replace(
        "{{KTM_CREATE_DESCRIPTION_JSON_STRING}}", json.dumps("description")
    )
    payload = payload.replace("{{KTM_CREATE_AUTHOR_JSON_STRING}}", json.dumps("author"))
    return cast(dict[str, Any], json.loads(payload))


class RuntimePackageContractTests(unittest.TestCase):
    def test_ktm_package_coordinates_use_libkt_naming(self) -> None:
        sdk = load_manifest(ROOT / "package.ktm.json")
        self.assertEqual(
            (sdk["metadata"]["namespace"], sdk["metadata"]["name"]),
            ("kinematic-trees", "kt-python-sdk"),
        )
        runtime = [
            item
            for item in sdk["dependencies"]["packages"]
            if item["classification"] == "library"
        ]
        self.assertEqual(
            [(item["owner"], item["name"], item["version"]) for item in runtime],
            [("kinematic-trees", "libkt", "0.1.1")],
        )

        template = load_manifest(ROOT / "template-package" / "package.ktm.json")
        self.assertEqual(
            (template["metadata"]["namespace"], template["metadata"]["name"]),
            ("kinematic-trees", "kt-python-template"),
        )
        template_sdk = [
            item
            for item in template["dependencies"]["packages"]
            if item["classification"] == "library"
        ]
        self.assertEqual(
            [(item["owner"], item["name"], item["version"]) for item in template_sdk],
            [("kinematic-trees", "kt-python-sdk", "0.2.0")],
        )

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
                        "owner": "kinematic-trees",
                        "name": "kt-messages",
                        "version": "0.1.0",
                        "classification": "data_types",
                    },
                )
                self.assertEqual(
                    set(messages[0]["environments"].values()), {"portable"}
                )

    def test_generated_starters_import_all_datatype_namespaces(self) -> None:
        paths = [
            ROOT / "boilerplate" / "src" / "{{KTM_CREATE_MODULE_NAME}}" / "robot.py.template",
            ROOT
            / "template-package"
            / "boilerplate"
            / "src"
            / "{{KTM_CREATE_MODULE_NAME}}"
            / "robot.py.template",
        ]
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                source = path.read_text(encoding="utf-8")
                self.assertIn("from kt.messages import *", source)
                compile(source, str(path), "exec")


if __name__ == "__main__":
    unittest.main()
