from __future__ import annotations

import json
import pathlib
import unittest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9-3.10 source-test compatibility
    tomllib = None  # type: ignore[assignment]

ROOT = pathlib.Path(__file__).resolve().parents[2]
BOILERPLATES = (ROOT / "template-package" / "boilerplate",)
RAW_STRUCTURED_TOKENS = (
    "{{KTM_CREATE_DESCRIPTION}}",
    "{{KTM_CREATE_AUTHOR}}",
)
TYPED_TOKENS = {
    "DESCRIPTION_JSON_STRING",
    "AUTHOR_JSON_STRING",
    "DESCRIPTION_TOML_STRING",
    "AUTHOR_TOML_STRING",
}


def render_template(source: str, values: dict[str, str]) -> str:
    for name, value in values.items():
        source = source.replace(f"{{{{KTM_CREATE_{name}}}}}", value)
    return source


def parse_project_metadata(source: str) -> dict[str, object]:
    if tomllib is not None:
        return dict(tomllib.loads(source)["project"])
    project: dict[str, object] = {}
    for line in source.splitlines():
        if line.startswith("description = "):
            project["description"] = json.loads(line.removeprefix("description = "))
        elif line.startswith("authors = [{name = ") and line.endswith("}]"):
            literal = line.removeprefix("authors = [{name = ").removesuffix("}]")
            project["authors"] = [{"name": json.loads(literal)}]
    return project


class TemplateMetadataSerializationTests(unittest.TestCase):
    def test_structured_templates_declare_and_use_typed_literals(self) -> None:
        for root in BOILERPLATES:
            with self.subTest(root=root):
                metadata = json.loads((root / "ktm-template.json").read_text())
                placeholders = set(metadata["placeholders"])
                self.assertTrue(TYPED_TOKENS <= placeholders)
                self.assertNotIn("DESCRIPTION", placeholders)
                self.assertNotIn("AUTHOR", placeholders)
                self.assertEqual(
                    metadata["literalContexts"],
                    {
                        "package.ktm.json.template": "json",
                        "pyproject.toml.template": "toml",
                    },
                )

                manifest_source = (root / "package.ktm.json.template").read_text()
                pyproject_source = (root / "pyproject.toml.template").read_text()
                for token in RAW_STRUCTURED_TOKENS:
                    self.assertNotIn(token, manifest_source)
                    self.assertNotIn(token, pyproject_source)
                self.assertIn("{{KTM_CREATE_DESCRIPTION_JSON_STRING}}", manifest_source)
                self.assertIn("{{KTM_CREATE_AUTHOR_JSON_STRING}}", manifest_source)
                self.assertIn("{{KTM_CREATE_DESCRIPTION_TOML_STRING}}", pyproject_source)
                self.assertIn("{{KTM_CREATE_AUTHOR_TOML_STRING}}", pyproject_source)

    def test_special_metadata_round_trips_through_json_and_toml(self) -> None:
        description = 'Robot "alpha" path C:\\robots\nTabbed\tUnicode 温度'
        author = 'Ada \\ Lovelace "team" 温度'
        values = {
            "PACKAGE_NAME": "demo-robot",
            "NAMESPACE": "demo-owner",
            "DESCRIPTION_JSON_STRING": json.dumps(description, ensure_ascii=False),
            "AUTHOR_JSON_STRING": json.dumps(author, ensure_ascii=False),
            "DESCRIPTION_TOML_STRING": json.dumps(description, ensure_ascii=False),
            "AUTHOR_TOML_STRING": json.dumps(author, ensure_ascii=False),
            "LANGUAGE": "python",
            "RUN_ENVIRONMENTS_JSON": "[]",
            "RUNTIME_SDK": "python",
        }
        for root in BOILERPLATES:
            with self.subTest(root=root):
                manifest = json.loads(
                    render_template(
                        (root / "package.ktm.json.template").read_text(), values
                    )
                )
                project = parse_project_metadata(
                    render_template(
                        (root / "pyproject.toml.template").read_text(), values
                    )
                )
                self.assertEqual(manifest["metadata"]["description"], description)
                self.assertEqual(manifest["metadata"]["author"], author)
                self.assertEqual(project["description"], description)
                self.assertEqual(project["authors"], [{"name": author}])

if __name__ == "__main__":
    unittest.main()
