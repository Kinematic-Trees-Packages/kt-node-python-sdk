import json

import pytest

from ktnode import ChannelContractError, ChannelContractIndex, UnknownChannelError


def write_package(tmp_path, inputs=None, outputs=None):
    package = tmp_path / "node.package.json"
    package.write_text(
        json.dumps({"dataflow": {"inputs": inputs or [], "outputs": outputs or []}}),
        encoding="utf-8",
    )
    return package


def test_index_resolves_exact_direction_and_datatype(tmp_path):
    package = write_package(
        tmp_path,
        inputs=[{"name": "request", "datatype": "kt/speech/string_sample", "required": True}],
        outputs=[{"name": "response", "datatype": "kt/speech/string_sample"}],
    )
    index = ChannelContractIndex.from_package(package)
    assert index.input("request").datatype == "kt/speech/string_sample"
    assert index.input("request").required is True
    assert index.output("response").direction == "output"
    with pytest.raises(UnknownChannelError, match="output, not an input"):
        index.input("response")
    with pytest.raises(UnknownChannelError, match="unknown output channel"):
        index.output("missing")


@pytest.mark.parametrize(
    "inputs, outputs, message",
    [
        ([{"name": "x", "datatype": "kt/a"}, {"name": "x", "datatype": "kt/b"}], [], "duplicate input"),
        ([{"name": "x", "datatype": "kt/a"}], [{"name": "x", "datatype": "kt/a"}], "unique across"),
        ([{"name": "", "datatype": "kt/a"}], [], "name must be"),
        ([{"name": "x", "datatype": ""}], [], "datatype must be"),
    ],
)
def test_index_rejects_ambiguous_or_incomplete_contracts(tmp_path, inputs, outputs, message):
    package = write_package(tmp_path, inputs=inputs, outputs=outputs)
    with pytest.raises(ChannelContractError, match=message):
        ChannelContractIndex.from_package(package)


def test_contract_mappings_are_immutable(tmp_path):
    index = ChannelContractIndex.from_package(
        write_package(tmp_path, inputs=[{"name": "x", "datatype": "kt/a"}])
    )
    with pytest.raises(TypeError):
        index.inputs["y"] = index.input("x")
