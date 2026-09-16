# Python HTML documentation conformance

Goal 7 validation completed on 2026-09-16 for SDK v0.2 source.

## Production artifact

- Generator: MkDocs 1.6.1, Material 9.6.14, mkdocstrings 0.29.1.
- Output path: `build/docs/v0.2`.
- Artifact: `build/docs-artifacts/kt-node-python-sdk-docs-v0.2.tar.gz`.
- Scope: 22 generated HTML pages with local search and generated Python API reference.
- Reproducibility: two clean builds produced identical SHA-256
  `ced7cad4aaa9edc169a44ea0a5307afaba8cbd22e7a7074710aea9233b5b1489`.

## Automated evidence

- 29 Python tests passed, including executable documentation examples and all
  Markdown Python fences.
- Strict MkDocs build passed from `python:3.12-slim` with only declared
  `test,docs` extras.
- Generated-site validator confirmed all internal links, required artifacts,
  local search, navigation/title structure, and every exported public symbol.
- Axe browser audits passed on the title, create-project, API-reference, and
  troubleshooting pages.
- Ruff and Mypy passed on changed SDK/documentation surfaces.
- The static tarball is byte-identical across clean builds.

## Clean developer path

With an empty temporary home and no existing KTM store, the documented path:

```bash
ktm create my-process --language python
cd my-process
ktm dev
ktm test
```

downloaded seven public registry artifacts, created the project, loaded KT Node
ABI 1.2, and passed both development and test smoke paths. The repository
automates this as `scripts/docs_quickstart_smoke.sh`.

## Explicit boundaries

- The site is a deployable static artifact; hosting/domain/version retention
  remain external deployment decisions.
- The `summer` page intentionally states that the detached package is pending
  Goal 8 rather than publishing untested commands.
- KT-LAN, WebRTC, non-Linux platforms, non-x86_64 architectures, and typed
  non-vision datatypes remain explicitly unproven.
