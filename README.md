# sm-model-provenance

Model provenance metadata for [NANDA](https://projectnanda.org)-compatible agent discovery.

A single dataclass that serializes model identity and versioning into the JSON shapes expected by NANDA AgentFacts, AgentCard, and decision-envelope outputs. Zero runtime dependencies.

## Installation

```bash
pip install git+https://github.com/Sharathvc23/sm-model-provenance.git
```

## Quick Start

```python
from sm_model_provenance import ModelProvenance

provenance = ModelProvenance(
    model_id="llama-3.1-8b",
    model_version="1.0.0",
    provider_id="ollama",
    model_type="base",
    governance_tier="standard",
)

provenance.to_dict()                    # {"model_id": "llama-3.1-8b", ...}
provenance.to_agentfacts_extension()    # {"x_model_provenance": {...}}
provenance.to_agent_card_metadata()     # {"model_info": {...}}
provenance.to_decision_fields()         # {"model_id": ..., "provider_id": ...}
```

## Output Formats

```
ModelProvenance
    ├── to_agentfacts_extension()  →  {"x_model_provenance": {...}}
    ├── to_agent_card_metadata()   →  {"model_info": {...}}
    └── to_decision_fields()       →  {"model_id": ..., "provider_id": ...}
```

| Format | Target | Fields included |
|--------|--------|-----------------|
| AgentFacts extension | NANDA AgentFacts `metadata` | All non-empty fields under `x_model_provenance` |
| AgentCard metadata | NANDA AgentCard `model_info` | All non-empty fields under `model_info` |
| Decision envelope | Flat top-level fields | `model_id`, `model_version`, `provider_id` only |

The default AgentFacts extension key is `x_model_provenance` (vendor-neutral, following the NANDA `x_` prefix convention). Vendors can use their own namespace:

```python
provenance.to_agentfacts_extension(extension_key="x_myvendor")
```

## Model Types

| Type | Description |
|------|-------------|
| `base` | Foundation / pre-trained models |
| `lora_adapter` | LLM LoRA fine-tuned adapters |
| `onnx_edge` | Edge ONNX / TFLite models |
| `federated` | Federated learning models |
| `heuristic` | Rule-based / heuristic fallbacks |

## Governance Tiers

| Tier | Description |
|------|-------------|
| `standard` | Default governance classification |
| `regulated` | Subject to additional policy requirements |

## Risk Levels

| Level | Description |
|-------|-------------|
| `low` | Minimal blast radius |
| `medium` | Moderate impact on failure |
| `high` | Requires additional governance approval |

## API

### ModelProvenance

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_id` | `str` | *(required)* | Model identifier (e.g. `"llama-3.1-8b"`) |
| `model_version` | `str` | `""` | Semantic or arbitrary version string |
| `provider_id` | `str` | `""` | Inference provider (`"openai"`, `"ollama"`, `"local"`) |
| `model_type` | `str` | `""` | Model category (see Model Types) |
| `base_model` | `str` | `""` | Foundation model name (when model_type is an adapter) |
| `governance_tier` | `str` | `""` | Governance classification (see Governance Tiers) |
| `weights_hash` | `str` | `""` | SHA-256 hex digest of model weights |
| `risk_level` | `str` | `""` | Risk assessment (see Risk Levels) |

All optional fields default to `""` and are omitted from serialized output.

**Methods**: `to_dict()`, `to_agentfacts_extension()`, `to_agent_card_metadata()`, `to_decision_fields()`, `from_dict()`

## Related Packages

| Package | Question it answers |
|---------|-------------------|
| `sm-model-provenance` (this package) | "Where did this model come from?" (identity, versioning, provider, NANDA serialization) |
| [`sm-model-card`](https://github.com/Sharathvc23/sm-model-card) | "What is this model?" (unified metadata schema — type, status, risk level, metrics, weights hash) |
| [`sm-model-integrity-layer`](https://github.com/Sharathvc23/sm-model-integrity-layer) | "Does this model's metadata meet policy?" (rule-based checks) |
| [`sm-model-governance`](https://github.com/Sharathvc23/sm-model-governance) | "Has this model been cryptographically approved for deployment?" (approval flow with signatures, quorum, scoping, revocation) |
| [`sm-bridge`](https://github.com/Sharathvc23/sm-bridge) | "How do I expose this to the NANDA network?" (FastAPI router, AgentFacts models, delta sync) |

## Development

```bash
git clone https://github.com/Sharathvc23/sm-model-provenance.git
cd sm-model-provenance
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT

---

*Personal research contributions aligned with [Project NANDA](https://projectnanda.org) standards. [Stellarminds.ai](https://stellarminds.ai)*
