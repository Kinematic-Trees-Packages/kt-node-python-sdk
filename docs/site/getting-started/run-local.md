# Run and test locally

From a generated project:

```bash
ktm doctor
ktm dev
ktm test
```

`ktm dev` resolves dependencies and composes native search paths. `ktm test` runs project smoke tests in the same managed environment.

Manual Python tooling is useful only for SDK or toolchain debugging:

```bash
eval "$(ktm env --shell)"
python -m pytest
```

If manual execution cannot find `libkt_node`, return to `ktm dev` or inspect the composed environment with `ktm explain linking`.

The repository validates this exact registry-backed path in a disposable directory with `scripts/docs_quickstart_smoke.sh`.
