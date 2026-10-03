from __future__ import annotations

import ast
import json
import pathlib

from ktnode import Node


ROOT = pathlib.Path(__file__).resolve().parents[2]
BOILERPLATE = ROOT / "template-package" / "boilerplate"
PROCESS = BOILERPLATE / "src" / "{{KTM_CREATE_MODULE_NAME}}" / "process.py.template"


def _manifest(name: str) -> dict[str, object]:
    source = (BOILERPLATE / name).read_text(encoding="utf-8")
    source = source.replace("{{KTM_CREATE_DESCRIPTION_JSON_STRING}}", '"description"')
    source = source.replace("{{KTM_CREATE_AUTHOR_JSON_STRING}}", '"author"')
    source = source.replace("{{KTM_CREATE_RUN_ENVIRONMENTS_JSON}}", "[]")
    return json.loads(source)


def test_starter_exposes_all_four_explicit_callback_todos() -> None:
    source = PROCESS.read_text(encoding="utf-8")
    tree = ast.parse(source)
    process = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Process")
    methods = {
        node.name: node
        for node in process.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    expected = {
        "setup": "TODO: implement setup",
        "step": "TODO: implement step",
        "close": "TODO: implement close",
        "config_update": "TODO: implement config_update",
    }
    sdk_callbacks = {
        name
        for name, value in vars(Node).items()
        if not name.startswith("_") and callable(value)
    }
    assert sdk_callbacks == expected.keys()
    assert expected.keys() <= methods.keys()
    for name, message in expected.items():
        raises = [node for node in ast.walk(methods[name]) if isinstance(node, ast.Raise)]
        assert len(raises) == 1
        call = raises[0].exc
        assert isinstance(call, ast.Call)
        assert isinstance(call.func, ast.Name)
        assert call.func.id == "NotImplementedError"
        assert len(call.args) == 1
        assert isinstance(call.args[0], ast.Constant)
        assert call.args[0].value == message


def test_step_guidance_is_typed_commented_and_not_executable() -> None:
    source = PROCESS.read_text(encoding="utf-8")
    assert '# value = kt.Get(ctx, "example_input")' in source
    assert '#     kt.Set(ctx, "example_output", value)' in source
    assert "# return kt.NextStep.CONTINUE" in source

    tree = ast.parse(source)
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "Get" not in calls
    assert "Set" not in calls
    assert "get_raw" not in source
    assert "set_raw" not in source


def test_each_callback_todo_has_a_multiline_explanation() -> None:
    source = PROCESS.read_text(encoding="utf-8")
    paragraphs = {
        "setup": ("setup runs once before processing begins", "return a NextStep value"),
        "step": ("step contains one unit of process behavior", "next scheduling decision"),
        "close": ("close runs once during terminal cleanup", "completed its cleanup"),
        "config_update": ("config_update receives a proposed runtime configuration", "ConfigUpdateResult"),
    }
    for start, end in paragraphs.values():
        assert start in source
        assert end in source


def test_template_has_one_root_package_and_one_root_runtime_contract() -> None:
    package = _manifest("package.ktm.json.template")
    runtime = _manifest("runtime.json.template")

    assert package["dataflow"] == {
        "inputs": [
            {
                "name": "example_input",
                "datatype": "kt/speech/string_sample",
                "required": False,
            }
        ],
        "outputs": [
            {"name": "example_output", "datatype": "kt/speech/string_sample"}
        ],
    }
    assert runtime["package"] == "./package.ktm.json"
    assert package["runtime"] == {"sdk": "{{KTM_CREATE_RUNTIME_SDK}}", "languageVersion": ">=3.9"}
    assert "development" not in package
    assert "runtime.json" in package["files"]
    assert "runtime" not in package["files"]
    assert not (BOILERPLATE / "runtime").exists()
    assert not list(BOILERPLATE.rglob("node.package.json.template"))


def test_runtime_manifest_is_complete_but_approach_neutral() -> None:
    runtime = _manifest("runtime.json.template")
    assert runtime == {
        "schemaVersion": "4",
        "id": "{{KTM_CREATE_PACKAGE_NAME}}",
        "package": "./package.ktm.json",
        "channelDefaults": [],
        "channelOverrides": {},
        "config": {},
    }
    assert "transport" not in runtime
    assert "execution" not in runtime
    assert "scheduling" not in runtime


def test_public_entrypoint_runs_the_explicit_process() -> None:
    source = (
        BOILERPLATE
        / "src"
        / "{{KTM_CREATE_MODULE_NAME}}"
        / "__main__.py.template"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    run_call = next(
        node
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "kt"
        and node.func.attr == "run"
    )
    assert len(run_call.args) == 3
    assert isinstance(run_call.args[2], ast.Call)
    assert isinstance(run_call.args[2].func, ast.Name)
    assert run_call.args[2].func.id == "Process"
