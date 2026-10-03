# Minimum process contract

The versioned fixture at `tests/fixtures/minimum_process_contract/v1` freezes
the smallest useful typed Python process. Its documents stay distinct:

| Document | Version | Authority |
| --- | --- | --- |
| root package | `3` | release metadata, dependencies, files, recipes, channels, and config schema |
| root runtime configuration | `4` | instance identity, scheduling, routes, buffering, and config values |

## Typed increment example

The required logical input `value` and output `incremented` both use the
existing `kt/common/int64_value` datatype. Configuration `increment` is a
required integer with default `1`. Counts are dimensionless; no coordinate
frame applies.

The v1 input is single-source and is read with `ReadMode.ONE`.
`Message.source_id` is absent for its single HTTP source. Multiple sources are
invalid instead of being reduced nondeterministically. `Message.remote_time_ns`
is absent because HTTP does not supply a remote timestamp; the process must not
invent one. Timestamped output is outside ABI 1.2.

The explicit process entrypoint is an argument vector, not a shell string:

```text
python3 -m minimum_contract --package package.ktm.json --runtime runtime.json
```

Python addresses only `value` and `incremented`; `/value` and `/incremented`
are deployment-owned runtime routes.

## Required failures

Validation must fail with a boundary-specific diagnostic for a missing or
misclassified lifecycle dependency, a missing required input route, an unknown
route, a wrong datatype, a duplicate channel, or missing/non-integer
`increment`. Process execution must fail for malformed `Int64Value` bytes,
multiple sources, or signed-64-bit overflow.

## Proposed release-description decision

**Proposal, not current platform fact:** lifecycle-v3 `metadata.description`
is the authoring authority and a registry release snapshots it immutably.
Runtime-v4 cannot override package metadata, channels, or configuration schema.
