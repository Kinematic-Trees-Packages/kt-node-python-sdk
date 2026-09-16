# Create a project

```bash
ktm create my-process --language python
cd my-process
```

The generated project declares a KTM dependency on `kinematic-trees/kt-node` and a Python dependency on `kt-node-python-sdk>=0.2.0`.

Edit the generated `Robot` subclass. Process logic must depend on public SDK types only:

--8<-- "examples/snippets/minimal_node.py"

Package and runtime JSON define channels, scheduling, and transports without changing the Python class.
