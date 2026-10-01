# Create a project

```bash
ktm create my-process --language python
cd my-process
```

The generated project declares direct KTM dependencies on the Python SDK and
`kinematic-trees/kt-messages`. KTM downloads and composes the SDK, all datatype
bindings, the FlatBuffers runtime, and the native KT Node runtime.

The starter makes every datatype namespace available without flattening
colliding generated names:

```python
from kt.messages import *

# Schema-qualified generated module.
image_sample_module = vision_sample.ImageSample
```

Edit the generated `Robot` subclass. Process logic must depend on public SDK types only:

--8<-- "examples/snippets/minimal_node.py"

Package and runtime JSON define channels, scheduling, and transports without changing the Python class.
