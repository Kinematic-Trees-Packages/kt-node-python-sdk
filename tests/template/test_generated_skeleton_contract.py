from __future__ import annotations

import ast
import json
import pathlib

from ktnode import Node


ROOT = pathlib.Path(__file__).resolve().parents[2]
BOILERPLATE = ROOT / "template-package" / "boilerplate"
ROBOT = BOILERPLATE / "src" / "{{KTM_CREATE_MODULE_NAME}}" / "robot.py.template"


def _manifest(name: str) -> dict[str, object]:
    source = (BOILERPLATE / name).read_text(encoding="utf-8")
    source = source.replace("{{KTM_CREATE_DESCRIPTION_JSON_STRING}}", '"description"')
    source = source.replace("{{KTM_CREATE_AUTHOR_JSON_STRING}}", '"author"')
    source = source.replace("{{KTM_CREATE_RUN_ENVIRONMENTS_JSON}}", "[]")
    return json.loads(source)


def test_starter_exposes_all_four_explicit_callback_todos() -> None:
    source = ROBOT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    robot = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Robot")
    methods = {
        node.name: node
        for node in robot.body
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
    source = ROBOT.read_text(encoding="utf-8")
    assert '# value = Get(ctx, "example_input")' in source
    assert '#     Set(ctx, "example_output", value)' in source
    assert "# return NextStep.CONTINUE" in source

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


def test_package_and_node_manifests_declare_the_same_string_channels() -> None:
    package = _manifest("package.ktm.json.template")
    node = _manifest("runtime/node.package.json.template")

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
    node_dataflow = node["dataflow"]
    assert [
        {key: value for key, value in channel.items() if key != "description"}
        for channel in node_dataflow["inputs"]
    ] == package["dataflow"]["inputs"]
    assert [
        {key: value for key, value in channel.items() if key != "description"}
        for channel in node_dataflow["outputs"]
    ] == package["dataflow"]["outputs"]


def test_runtime_manifest_is_complete_but_approach_neutral() -> None:
    runtime = _manifest("runtime/runtime.json.template")
    assert runtime == {
        "schemaVersion": "4",
        "id": "{{KTM_CREATE_PACKAGE_NAME}}",
        "package": "node.package.json",
        "channelDefaults": [],
        "channelOverrides": {},
        "config": {},
    }
    assert "transport" not in runtime
    assert "execution" not in runtime
    assert "scheduling" not in runtime


def test_public_entrypoint_runs_the_explicit_robot() -> None:
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
        if isinstance(node.func, ast.Name) and node.func.id == "run"
    )
    assert len(run_call.args) == 3
    assert isinstance(run_call.args[2], ast.Call)
    assert isinstance(run_call.args[2].func, ast.Name)
    assert run_call.args[2].func.id == "Robot"
