# Repository ownership and layout

This document is the ownership contract for the Python SDK repository.

## Stable public surface

- KTM package coordinate: `kinematic-trees/kt-python-sdk`
- Python distribution: `kt-python-sdk`
- Python import package: `ktnode`
- Source authority: `python/ktnode`
- Wheel baseline: `ktnode/__init__.py`, `abi.py`, `channels.py`,
  `errors.py`, `runtime.py`, and `py.typed`, plus wheel
  metadata. Repository cleanup must not add templates, examples, or tests to
  the wheel.

## Owned paths

| Path | Purpose |
| --- | --- |
| `python/ktnode` | Public SDK implementation and typing marker |
| `template-package/boilerplate` | Sole source for `ktm create --language python` |
| `tests/unit` | Fast isolated behavior tests |
| `tests/contract` | Package, documentation, and compatibility contracts |
| `tests/template` | Generated starter behavior and metadata |
| `tests/integration` | Real runtime/transport probes |
| `tests/fixtures` | Versioned deterministic test projects and peers |
| `examples` | Supported SDK examples |
| `examples/stress` | Manual or dependency-heavy stress tools |

There must be no second root-level `boilerplate` tree. A completed example
used for acceptance belongs under a versioned test fixture and must not replace
the intentionally incomplete public starter.
