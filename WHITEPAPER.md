# Model Identity Metadata for Federated AI Agent Discovery

**Authors:** StellarMinds ([stellarminds.ai](https://stellarminds.ai))
**Date:** April 2026
**Version:** 0.2.0

## Abstract

`sm-model-provenance` is a zero-dependency Python dataclass that captures model identity and versioning in eight typed fields and serializes them into three distinct JSON shapes expected by the NANDA agent ecosystem. It solves the problem of model identity being entangled with heavier concerns like integrity verification, lifecycle management, and cryptographic governance. The library uses an omit-when-empty serialization pattern that produces compact payloads suitable for network transmission and supports forward-compatible deserialization that silently ignores unknown keys. The implementation uses only Python's `dataclasses` module.

## Problem

When an AI agent in a decentralized registry advertises its capabilities, consuming agents need to answer a foundational question: "What model is this agent using, and where did it come from?" This model identity information — name, version, inference provider, type, and governance classification — is the prerequisite for all downstream trust decisions.

In practice, this identity metadata is often entangled with heavier concerns. Integrity verification systems bundle identity with cryptographic hashing and attestation. Model card schemas embed identity within rich documentation formats with lifecycle management and training metrics. Governance frameworks wrap identity in approval workflows and signature chains. Each coupling introduces dependencies and complexity that may not be appropriate for every consumer. A registry that simply wants to advertise "this agent uses llama-3.1-8b via ollama" should not need a cryptography library, a model card parser, or a governance framework.

## What It Does

- Captures model identity in 8 typed fields: `model_id` (required), `model_version`, `provider_id`, `model_type`, `base_model`, `governance_tier`, `weights_hash`, `risk_level`
- Serializes to 3 distinct JSON shapes: AgentFacts extension (`x_model_provenance`), AgentCard metadata (`model_info`), and decision-envelope fields (3 fields only)
- Omits empty fields automatically via truthiness filtering (`{k: v for ... if v}`) for compact network payloads
- Deserializes forward-compatibly by reading only known fields via `.get()` and silently ignoring unknown keys from future schema versions
- Supports vendor-neutral extension key (`x_model_provenance`) with opt-in vendor namespacing via the `extension_key` parameter
- Provides lossless round-trip: `ModelProvenance.from_dict(p.to_dict()) == p` holds for all valid instances
- Raises `TypeError` (not `ValueError`) for missing `model_id`, aligning with Python's convention for missing required arguments
- Uses `@dataclass` rather than Pydantic, eliminating all runtime dependencies while keeping the type as a plain data container
- Requires zero external dependencies — uses only Python's `dataclasses` module

## Architecture

The library produces three distinct JSON shapes from the same underlying 8-field dataclass, each targeting a different NANDA integration point:

| Output Method | JSON Shape | Fields Included | Use Case |
|---------------|-----------|-----------------|----------|
| `to_agentfacts_extension()` | `{"x_model_provenance": {...}}` | All non-empty | NANDA AgentFacts `metadata` vendor extension |
| `to_agent_card_metadata()` | `{"model_info": {...}}` | All non-empty | NANDA AgentCard profile |
| `to_decision_fields()` | `{"model_id": ..., ...}` | `model_id`, `model_version`, `provider_id` only | Decision audit envelope records |

All three methods share a common `to_dict()` base with omit-when-empty semantics. The first two methods produce complete provenance snapshots nested under their respective keys. The third deliberately restricts output to three identity-core fields using explicit field-by-field construction (rather than filtering `to_dict()`), matching the minimal provenance footprint expected in decision-envelope audit records where payload size matters. The `to_agentfacts_extension()` key defaults to `x_model_provenance` but is parameterizable for vendor-specific namespacing. The `to_agent_card_metadata()` key is fixed at `model_info` because the NANDA AgentCard specification defines it as a reserved key.

```
ModelProvenance (8 fields)
         │
         ├──▶ to_agentfacts_extension()  ──▶  {"x_model_provenance": {...}}
         │                                      └─ NANDA AgentFacts metadata
         │
         ├──▶ to_agent_card_metadata()   ──▶  {"model_info": {...}}
         │                                      └─ NANDA AgentCard profile
         │
         └──▶ to_decision_fields()       ──▶  {"model_id", "model_version", "provider_id"}
                                                └─ Decision envelope (3 fields only)
```

The eight fields are organized into three semantic groups:

| Group | Fields | Purpose |
|-------|--------|---------|
| Identity | `model_id`, `model_version`, `provider_id` | Core model identification |
| Classification | `model_type`, `base_model`, `governance_tier` | Paradigm and governance categorization |
| Integrity-linking | `weights_hash`, `risk_level` | Bridge to integrity layer without depending on it |

The `model_id` field is the only required field. All other fields default to empty strings. A minimal provenance record with only `model_id` set serializes to a single key-value pair (`{"model_id": "test"}`). A typical record with three fields set produces three key-value pairs. A full record with all eight fields populated produces the complete provenance snapshot with no empty-string noise. This progressive compactness means consumers pay only for the metadata they actually set.

The identity fields (`model_id`, `model_version`, `provider_id`) identify what model is running and who is serving it. The classification fields (`model_type`, `base_model`, `governance_tier`) categorize the model's paradigm and governance requirements. The integrity-linking fields (`weights_hash`, `risk_level`) allow provenance records to carry integrity-relevant metadata without creating a dependency on the integrity layer itself — they serve as a bridge between identity and verification.

The `extension_key` parameter on `to_agentfacts_extension()` defaults to `x_model_provenance` following the NANDA `x_` prefix convention for vendor extensions, analogous to HTTP's `X-` header prefix. The default promotes cross-registry interoperability while the parameter enables vendor-specific namespacing when needed.

The `from_dict()` class method provides forward-compatible deserialization: it reads only the eight known fields via `.get()` with empty-string defaults. If a future schema version adds a ninth field, existing library versions can still deserialize the record without error. The single required field (`model_id`) raises `TypeError` when missing, aligning with Python's convention for missing required arguments.

## Key Design Decisions

- **Empty string defaults, not `None`:** All optional fields default to `""` rather than `None`. This enables a uniform truthiness filter (`if v`) without `Optional` type annotations, simplifies equality comparisons, and produces cleaner `repr()` output. The trade-off is that the type signature `str` does not distinguish "not set" from "explicitly set to empty," but in practice provenance fields are never meaningfully set to empty strings, so this ambiguity does not arise.

- **Explicit field maps, not `asdict()`:** `to_dict()` constructs an explicit field map rather than using `dataclasses.asdict()`. This serves two purposes: it controls field ordering to match the NANDA bridge's expected order for byte-identical output, and it avoids the deep-copy behavior of `asdict()` which would be unnecessary overhead for a flat string-only dataclass. The explicit map also makes the serialization contract visible in the code rather than implicit.

- **Only 3 fields in decision envelope:** `to_decision_fields()` restricts output to `model_id`, `model_version`, and `provider_id` using explicit field-by-field construction rather than filtering `to_dict()`. Decision envelopes are high-volume audit records where payload minimality matters. Including `model_type`, `governance_tier`, or `weights_hash` in every decision record would add noise without improving routing decisions. The restriction is deliberately visible in the code.

- **No enum validation on type/tier/risk fields:** Fields like `model_type`, `governance_tier`, and `risk_level` accept arbitrary strings rather than validating against an enum or frozenset. This keeps the identity layer forward-compatible with new values added by downstream packages (the integrity layer adds `quantized`, `distilled`, `merged`; the governance layer adds `restricted` tier) and avoids coupling the identity layer to classification decisions that belong at the policy level.

## Ecosystem Integration

The `sm-model-provenance` package occupies the identity layer in the NANDA ecosystem, providing the foundational metadata type that three companion packages build upon.

| Package | Role | Question Answered |
|---------|------|-------------------|
| **`sm-model-provenance`** | **Identity metadata** | **Where did this model come from?** |
| `sm-model-card` | Metadata schema | What is this model? |
| `sm-model-integrity-layer` | Integrity verification | Does metadata meet policy? |
| `sm-model-governance` | Cryptographic governance | Has this model been approved? |
| `sm-bridge` | Transport layer | How is it exposed to the network? |

The model card package shares five fields with provenance (`model_id`, `model_type`, `base_model`, `weights_hash`, `risk_level`) by design: provenance carries the identity subset so systems that only need "who is this model" can avoid the full model card dependency. The integrity layer extends the identity schema with 3 additional fields (`hash_algorithm`, `created_at`, `attestation_method`) that capture how and when provenance was verified. The governance layer captures `model_id` and `weights_hash` in its `TrainingOutput` handoff, establishing the identity anchor for the governance decision.

In a NANDA agent discovery flow, provenance metadata participates at each stage:

1. **Registration** — An agent's `ModelProvenance` is serialized via `to_agentfacts_extension()` and merged into the agent's AgentFacts metadata.
2. **Discovery** — A consuming agent queries the registry, receives AgentFacts, and extracts the inner provenance dict from the `x_model_provenance` key.
3. **Reconstruction** — The consumer calls `ModelProvenance.from_dict()` on the extracted dict to reconstruct a typed provenance object.
4. **Routing** — The consumer uses `model_type`, `provider_id`, and `governance_tier` to make routing decisions without needing the full integrity or governance stack.

The package exports two symbols: `ModelProvenance` (the core identity metadata class) and `__version__` (the package version string). This minimal public API reflects the library's role as a foundational building block: it provides identity metadata and nothing more. Validation of field values (e.g., whether `model_type` is a recognized category or `risk_level` is within bounds) is deliberately omitted — that responsibility belongs to the integrity layer and governance layer, which operate at higher abstraction levels with their own policy engines.

The dataclass design over Pydantic is intentional: using Python's `@dataclass` rather than Pydantic models eliminates all runtime dependencies. The provenance type is a plain data container without validation logic, keeping it deployable in every environment from edge devices to serverless functions without pulling in any third-party packages.

## References

1. NANDA Protocol. "Network of AI Agents in Decentralized Architecture." https://projectnanda.org
2. W3C. "PROV-DM: The PROV Data Model." https://www.w3.org/TR/prov-dm/

---

*First published: 2026-04-15 | Last modified: 2026-04-15*

*[stellarminds.ai](https://stellarminds.ai) — Research Contribution to [Project NANDA](https://projectnanda.org)*
