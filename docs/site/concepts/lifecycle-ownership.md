# Lifecycle and ownership

`Node` has three lifecycle callbacks and one optional configuration callback:

1. `setup(ctx)`
2. zero or more `step(ctx)` calls
3. `close(ctx)` for terminal cleanup
4. `config_update(ctx, update)` when V2 configuration changes arrive

`Runtime` owns the native runtime. Prefer a context manager:

```python
with Runtime(package_path, runtime_path, node) as runtime:
    runtime.run()
```

## Borrowed callback context

`Context` is valid only during its callback. The SDK invalidates it on return; later use raises `ClosedResourceError`. Context calls from another thread are rejected by the native ABI. Callbacks do not overlap, but may run on different runtime worker threads.

## Payload ownership

Python payloads passed to `set` or `set_from` are copied. Message batches, errors, and owned JSON byte buffers are destroyed by the SDK after copying their data.

## Terminal behavior

- `NextStep.STOP` requests successful termination.
- `NextStep.RECOVERABLE` allows another step when scheduling permits.
- `NextStep.FATAL` fails the callback.
- Python exceptions are contained, reported, and converted to fatal outcomes.
- A close-callback failure is logged but does not replace an otherwise successful run result.
