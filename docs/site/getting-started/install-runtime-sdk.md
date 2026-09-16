# Install the runtime and Python SDK

The SDK and runtime are separate artifacts:

- `kt-node-python-sdk` provides the `ktnode` Python package.
- `kinematic-trees/kt-node` provides `libkt_node`, the C header, schemas, and runtime dependency metadata.

The recommended path is a KTM-created project because KTM installs both and composes `LD_LIBRARY_PATH` or equivalent platform paths.

```bash
ktm create my-process --language python
cd my-process
ktm dev
```

For SDK development without the native runtime:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -c 'import ktnode; print(ktnode.__all__)'
```

Importing `ktnode` does not load the native library. Constructing `Runtime` does. See [library discovery failures](../troubleshooting.md#native-library-discovery).
