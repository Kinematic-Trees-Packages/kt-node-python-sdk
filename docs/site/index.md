---
title: KT Node Python SDK
description: The tested Python reference SDK for portable Kinematic Trees processes.
---

<section class="hero" aria-labelledby="hero-title">
  <div class="hero__eyebrow">Python reference implementation · v0.2</div>
  <h1 id="hero-title">Build a process once. Choose transport at runtime.</h1>
  <p>The KT Node Python SDK lets process code use lifecycle callbacks and named byte channels without importing Rust internals or compiling runtime source.</p>
  <div class="hero__actions">
    <a class="md-button md-button--primary" href="getting-started/install-ktm/">Install KTM</a>
    <a class="md-button" href="getting-started/create-project/">Create a Python process</a>
    <a class="md-button" href="concepts/runtime-process/">Understand the runtime model</a>
  </div>
</section>

## From project to running code

```bash
ktm create my-process --language python
cd my-process
ktm dev
ktm test
```

KTM resolves the native runtime, composes its environment, and creates an editable project. Application code imports only the public `ktnode` SDK.

--8<-- "examples/snippets/minimal_node.py"

## Supported languages

<div class="support-grid">
  <div class="support-card"><strong>Python</strong><br>Supported reference implementation</div>
  <div class="support-card"><strong>C++</strong><br>SDK preview; not documented as conformant here</div>
  <div class="support-card"><strong>Go</strong><br>SDK preview; not documented as conformant here</div>
  <div class="support-card"><strong>C#</strong><br>SDK preview; not documented as conformant here</div>
</div>

## Tested contract

- Python 3.9–3.12 syntax and unit coverage
- KT Node C ABI 1.2, with V2 construction and V1 fallback
- HTTP and KT SHM transport slices
- Opaque-byte data flow and typed RGB vision helper
- KTM `compiled` and `compiled-source` packaging modes

[Check exact compatibility and limitations](compatibility.md){ .md-button }
