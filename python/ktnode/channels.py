"""Validated channel contracts for manifest-driven Python SDK access."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .errors import ChannelContractError, UnknownChannelError


@dataclass(frozen=True)
class ChannelContract:
    """One exact channel-to-datatype declaration from the node package."""

    name: str
    datatype: str
    direction: str
    required: bool = False


class ChannelContractIndex:
    """Immutable input/output lookup built once for a runtime instance."""

    __slots__ = ("_inputs", "_outputs")

    _inputs: Mapping[str, ChannelContract]
    _outputs: Mapping[str, ChannelContract]

    def __init__(
        self,
        inputs: Mapping[str, ChannelContract],
        outputs: Mapping[str, ChannelContract],
    ) -> None:
        object.__setattr__(self, "_inputs", MappingProxyType(dict(inputs)))
        object.__setattr__(self, "_outputs", MappingProxyType(dict(outputs)))

    @classmethod
    def from_package(cls, package_path: str | Path) -> "ChannelContractIndex":
        path = Path(package_path)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ChannelContractError(f"cannot read node package {path}: {error}") from error
        if not isinstance(document, dict):
            raise ChannelContractError("node package must be a JSON object")
        dataflow = document.get("dataflow")
        if not isinstance(dataflow, dict):
            raise ChannelContractError("node package dataflow must be an object")
        inputs = cls._parse_direction(dataflow.get("inputs"), "input")
        outputs = cls._parse_direction(dataflow.get("outputs"), "output")
        overlap = sorted(set(inputs).intersection(outputs))
        if overlap:
            raise ChannelContractError(
                "channel names must be unique across inputs and outputs: "
                + ", ".join(overlap)
            )
        return cls(inputs, outputs)

    @staticmethod
    def _parse_direction(raw: object, direction: str) -> dict[str, ChannelContract]:
        if not isinstance(raw, list):
            raise ChannelContractError(f"node package dataflow.{direction}s must be an array")
        result: dict[str, ChannelContract] = {}
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ChannelContractError(f"dataflow.{direction}s[{index}] must be an object")
            name = item.get("name")
            datatype = item.get("datatype")
            if not isinstance(name, str) or not name:
                raise ChannelContractError(f"dataflow.{direction}s[{index}].name must be a non-empty string")
            if not isinstance(datatype, str) or not datatype:
                raise ChannelContractError(
                    f"dataflow.{direction}s[{index}].datatype must be a non-empty string"
                )
            if name in result:
                raise ChannelContractError(f"duplicate {direction} channel: {name}")
            required = item.get("required", False)
            if not isinstance(required, bool):
                raise ChannelContractError(f"dataflow.{direction}s[{index}].required must be boolean")
            result[name] = ChannelContract(name, datatype, direction, required)
        return result

    @property
    def inputs(self) -> Mapping[str, ChannelContract]:
        return self._inputs

    @property
    def outputs(self) -> Mapping[str, ChannelContract]:
        return self._outputs

    def input(self, name: str) -> ChannelContract:
        try:
            return self._inputs[name]
        except KeyError as error:
            if name in self._outputs:
                raise UnknownChannelError(f"channel {name!r} is an output, not an input") from error
            raise UnknownChannelError(f"unknown input channel: {name}") from error

    def output(self, name: str) -> ChannelContract:
        try:
            return self._outputs[name]
        except KeyError as error:
            if name in self._inputs:
                raise UnknownChannelError(f"channel {name!r} is an input, not an output") from error
            raise UnknownChannelError(f"unknown output channel: {name}") from error
