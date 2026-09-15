# Python SDK to KT Node ABI 1.2 contract matrix

The public Python API owns native resources and never exposes raw pointers as
the normal developer interface. `ktnode.abi` is internal implementation
detail. Every frozen ABI symbol is bound centrally and covered directly or by
the owning high-level operation.

| ABI symbol(s) | Python API / responsibility | Test evidence |
|---|---|---|
| `kt_abi_version_major`, `kt_abi_version_minor` | `Runtime` compatibility negotiation | `test_live_runtime_info_and_v2_selection` |
| `kt_runtime_version`, `kt_runtime_build_id`, `kt_runtime_capabilities_v1` | `Runtime.info` | `test_live_runtime_info_and_v2_selection` |
| `kt_runtime_create_v1`, `kt_runtime_create_v2` | `Runtime(...)`; V2 for ABI >=1.2 when exported, otherwise V1 | `test_live_runtime_info_and_v2_selection`, reviewed fallback branch |
| `kt_runtime_run` | `Runtime.run()` | runtime lifecycle tests |
| `kt_runtime_request_close` | `Runtime.request_close()` | runtime lifecycle tests |
| `kt_runtime_destroy` | `Runtime.close()`, `destroy()`, context manager | `test_runtime_rejects_use_after_close` and live close test |
| `kt_context_is_closing` | `Context.is_closing()` | callback-context tests |
| `kt_context_request_close` | `Context.request_close()` | callback-context tests |
| `kt_context_report_error` | `Context.report_error()` and callback exception trampoline | callback error tests |
| `kt_context_set` | `Context.set()` | data tests |
| `kt_context_set_source` | `Context.set_from()` | data tests |
| `kt_context_read` | `Context.get()` | data tests |
| `kt_message_batch_count`, `kt_message_batch_item`, `kt_message_batch_destroy` | owned internally by `Context.get()` | data tests |
| `kt_context_metrics_json` | `Context.metrics_json()`, `metrics()` | context tests |
| `kt_context_config_json` | `Context.config_json()`, `config()` | config callback tests |
| `kt_context_config_revision` | `Context.config_revision()` | config callback tests |
| `kt_owned_bytes_view`, `kt_owned_bytes_destroy` | owned internally by metrics/config accessors | context tests |
| `kt_status_name` | `_check_status()` fallback | `test_status_error_uses_status_name_without_error_object` |
| `kt_error_code`, `kt_error_message`, `kt_error_destroy` | `_check_status()` and public exception taxonomy | status/error tests |

Capability bits map to `Capability.HTTP`, `KT_LAN`, `KT_SHM`, and `WEBRTC`.
`Runtime.require_capability()` raises `UnsupportedCapabilityError` before a
feature-specific operation. ABI-major mismatches raise
`AbiCompatibilityError`; closed resources raise `ClosedResourceError`.
