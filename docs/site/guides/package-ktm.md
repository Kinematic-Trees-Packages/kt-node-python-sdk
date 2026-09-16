# Package with KTM

```bash
ktm build
ktm test
ktm pack --mode compiled
ktm pack --mode compiled-source
```

`compiled` contains the importable Python runtime payload and required metadata. `compiled-source` adds tests, examples, docs source, and development scripts. Both modes use explicit allowlists and profile or global exclusions.

Forbidden cache artifacts include `__pycache__`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, and `.ruff_cache`. KTM v1.2.20 or later is required for the v2 packaging contract, including assertions, deterministic inventory and provenance, limits, and `--list` or `--explain` diagnostics.

Do not vendor `libkt_node` into a normal process package. KTM owns dependency resolution for the runtime artifact.
