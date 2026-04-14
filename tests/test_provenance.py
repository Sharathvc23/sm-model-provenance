"""Unit tests for ModelProvenance dataclass and serialization methods.

# Step 1 — Assumption Audit
# - model_id is required and must be a non-empty string
# - All other 7 fields default to "" and are omitted from to_dict when empty
# - to_decision_fields only emits model_id / model_version / provider_id
# - from_dict ignores unknown keys; raises on missing/empty model_id
# - Equality is structural (dataclass __eq__)
#
# Step 2 — Gap Analysis
# - No stress test for very long model_id
# - No XSS / injection test — fields should store raw strings as-is
# - No test verifying to_dict output when only model_id is set (minimal)
# - No test for custom agentfacts extension keys with dots/hyphens
# - No explicit assertion that decision_fields never leaks weights_hash
# - No test for from_dict with non-string values in optional fields
# - No full 8-field round-trip test that checks equality
#
# Step 3 — Break It List
# - model_id = "<script>alert(1)</script>" — must store verbatim, no sanitization
# - from_dict({"model_id": "x", "model_version": 123}) — int in str field
# - 10 000-char model_id — should work, no truncation
# - Custom extension key "x-vendor.custom" — must pass through
"""

from __future__ import annotations

import pytest
from sm_model_provenance import ModelProvenance

# -- to_dict() --------------------------------------------------------


class TestToDict:
    """to_dict() serializes fields and omits empty strings."""

    def test_minimal_only_model_id(self):
        p = ModelProvenance(model_id="phi3-mini")
        assert p.to_dict() == {"model_id": "phi3-mini"}

    def test_maximal_all_fields(self):
        p = ModelProvenance(
            model_id="llama-3.1-8b",
            model_version="1.0.0",
            provider_id="ollama",
            model_type="base",
            base_model="llama-3.1-8b",
            governance_tier="standard",
            weights_hash="abc123",
            risk_level="low",
        )
        d = p.to_dict()
        assert d == {
            "model_id": "llama-3.1-8b",
            "model_version": "1.0.0",
            "provider_id": "ollama",
            "model_type": "base",
            "base_model": "llama-3.1-8b",
            "governance_tier": "standard",
            "weights_hash": "abc123",
            "risk_level": "low",
        }

    def test_omits_empty_strings(self):
        p = ModelProvenance(
            model_id="phi3-mini",
            model_version="3.8b",
            provider_id="",
            model_type="lora_adapter",
        )
        d = p.to_dict()
        assert "provider_id" not in d
        assert d == {
            "model_id": "phi3-mini",
            "model_version": "3.8b",
            "model_type": "lora_adapter",
        }

    def test_empty_model_id_raises(self):
        """model_id="" now raises ValueError at construction."""
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            ModelProvenance(model_id="")


# -- to_agentfacts_extension() ----------------------------------------


class TestAgentFactsExtension:
    """to_agentfacts_extension() wraps under an extension key."""

    def test_default_key(self):
        p = ModelProvenance(model_id="phi3-mini", provider_id="local")
        result = p.to_agentfacts_extension()
        assert "x_model_provenance" in result
        assert result["x_model_provenance"]["model_id"] == "phi3-mini"
        assert result["x_model_provenance"]["provider_id"] == "local"

    def test_custom_key(self):
        p = ModelProvenance(model_id="test")
        result = p.to_agentfacts_extension(extension_key="x_custom")
        assert "x_custom" in result
        assert "x_model_provenance" not in result
        assert result["x_custom"]["model_id"] == "test"


# -- to_agent_card_metadata() ----------------------------------------


class TestAgentCardMetadata:
    """to_agent_card_metadata() wraps under 'model_info'."""

    def test_shape(self):
        p = ModelProvenance(model_id="llama-3.1-8b", provider_id="ollama")
        result = p.to_agent_card_metadata()
        assert "model_info" in result
        assert result["model_info"] == {
            "model_id": "llama-3.1-8b",
            "provider_id": "ollama",
        }

    def test_minimal(self):
        p = ModelProvenance(model_id="test")
        result = p.to_agent_card_metadata()
        assert result == {"model_info": {"model_id": "test"}}


# -- to_decision_fields() --------------------------------------------


class TestDecisionFields:
    """to_decision_fields() emits flat top-level fields."""

    def test_all_three_present(self):
        p = ModelProvenance(
            model_id="phi3-mini",
            model_version="3.8b",
            provider_id="local",
        )
        assert p.to_decision_fields() == {
            "model_id": "phi3-mini",
            "model_version": "3.8b",
            "provider_id": "local",
        }

    def test_omits_empty(self):
        p = ModelProvenance(model_id="phi3-mini")
        result = p.to_decision_fields()
        assert result == {"model_id": "phi3-mini"}
        assert "model_version" not in result
        assert "provider_id" not in result

    def test_ignores_other_fields(self):
        """Decision fields only contain model_id/version/provider_id."""
        p = ModelProvenance(
            model_id="llama",
            model_type="base",
            governance_tier="regulated",
            weights_hash="abc",
            risk_level="high",
        )
        result = p.to_decision_fields()
        assert result == {"model_id": "llama"}

    def test_empty_model_id_raises(self):
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            ModelProvenance(model_id="", provider_id="ollama")


# -- from_dict() ------------------------------------------------------


class TestFromDict:
    """from_dict() deserializes and round-trips."""

    def test_minimal(self):
        p = ModelProvenance.from_dict({"model_id": "test"})
        assert p.model_id == "test"
        assert p.model_version == ""
        assert p.provider_id == ""

    def test_full_round_trip(self):
        original = ModelProvenance(
            model_id="llama-3.1-8b",
            model_version="1.0.0",
            provider_id="ollama",
            model_type="base",
            base_model="llama-3.1-8b",
            governance_tier="standard",
            weights_hash="deadbeef",
            risk_level="low",
        )
        rebuilt = ModelProvenance.from_dict(original.to_dict())
        assert rebuilt == original

    def test_ignores_unknown_keys(self):
        data = {"model_id": "test", "unknown_field": "ignored", "extra": 42}
        p = ModelProvenance.from_dict(data)
        assert p.model_id == "test"

    def test_missing_model_id_raises(self):
        with pytest.raises(ValueError, match="model_id is required"):
            ModelProvenance.from_dict({"provider_id": "ollama"})

    def test_round_trip_via_agentfacts(self):
        """from_dict can rebuild from to_agentfacts_extension inner dict."""
        original = ModelProvenance(model_id="phi3", provider_id="local")
        ext = original.to_agentfacts_extension()
        inner = ext["x_model_provenance"]
        rebuilt = ModelProvenance.from_dict(inner)
        assert rebuilt.model_id == "phi3"
        assert rebuilt.provider_id == "local"


# -- Input validation -------------------------------------------------


class TestInputValidation:
    """Validation of model_id in constructor and from_dict."""

    def test_constructor_none_model_id_raises(self):
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            ModelProvenance(model_id=None)  # type: ignore[arg-type]

    def test_constructor_empty_model_id_raises(self):
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            ModelProvenance(model_id="")

    def test_from_dict_missing_model_id_raises_valueerror(self):
        with pytest.raises(ValueError, match="model_id is required"):
            ModelProvenance.from_dict({"provider_id": "ollama"})

    def test_from_dict_non_string_model_id_raises(self):
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            ModelProvenance.from_dict({"model_id": 123})  # type: ignore[dict-item]

    def test_from_dict_empty_model_id_raises(self):
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            ModelProvenance.from_dict({"model_id": ""})


# -- Additional edge-case tests -------------------------------------------


class TestEdgeCases:
    """Edge-case tests for ModelProvenance."""

    def test_from_dict_with_unknown_keys_ignored(self):
        """from_dict silently drops keys not in the dataclass."""
        p = ModelProvenance.from_dict({"model_id": "test", "unknown_key": "value"})
        assert p.model_id == "test"
        assert not hasattr(p, "unknown_key")

    def test_from_dict_empty_dict_raises(self):
        """from_dict({}) raises ValueError because model_id is missing."""
        with pytest.raises(ValueError, match="model_id is required"):
            ModelProvenance.from_dict({})

    def test_to_dict_preserves_all_set_fields(self):
        """When all 8 fields are set, to_dict() returns all of them."""
        p = ModelProvenance(
            model_id="m",
            model_version="v",
            provider_id="p",
            model_type="t",
            base_model="b",
            governance_tier="g",
            weights_hash="w",
            risk_level="r",
        )
        d = p.to_dict()
        assert len(d) == 8
        assert d == {
            "model_id": "m",
            "model_version": "v",
            "provider_id": "p",
            "model_type": "t",
            "base_model": "b",
            "governance_tier": "g",
            "weights_hash": "w",
            "risk_level": "r",
        }

    def test_round_trip_full(self):
        """Full round-trip: construct -> to_dict -> from_dict -> equality."""
        original = ModelProvenance(
            model_id="roundtrip",
            model_version="2.0",
            provider_id="azure",
            model_type="lora_adapter",
            base_model="llama-3.1-70b",
            governance_tier="regulated",
            weights_hash="sha256abc",
            risk_level="high",
        )
        rebuilt = ModelProvenance.from_dict(original.to_dict())
        assert rebuilt == original

    def test_unicode_in_fields(self):
        """Unicode characters in model_id are handled correctly."""
        p = ModelProvenance(model_id="modèle-réseau-neuronal-\u00e9\u00e8\u00ea")
        assert "modèle" in p.model_id
        d = p.to_dict()
        assert d["model_id"] == p.model_id
        rebuilt = ModelProvenance.from_dict(d)
        assert rebuilt.model_id == p.model_id


# -- R1-R10 adversarial / boundary tests -------------------------------------

LONG_MODEL_ID = "m" * 10_000


class TestAdversarialBoundary:
    """Boundary, failure, and sad-path tests (R1-R10 protocol)."""

    # -- stress ---------------------------------------------------------------

    def test_extremely_long_model_id(self):
        """10 000-char model_id should be accepted and round-trip."""
        p = ModelProvenance(model_id=LONG_MODEL_ID)
        assert p.model_id == LONG_MODEL_ID
        rebuilt = ModelProvenance.from_dict(p.to_dict())
        assert rebuilt.model_id == LONG_MODEL_ID

    def test_special_characters_in_fields(self):
        """XSS-style payload in model_id is stored verbatim (no sanitization)."""
        xss = "test<script>alert(1)</script>"
        p = ModelProvenance(model_id=xss)
        assert p.model_id == xss
        d = p.to_dict()
        assert d["model_id"] == xss
        rebuilt = ModelProvenance.from_dict(d)
        assert rebuilt.model_id == xss

    # -- sad path / failure ---------------------------------------------------

    def test_to_dict_with_all_empty_optional_fields(self):
        """When only model_id is set, to_dict returns a single-key dict."""
        p = ModelProvenance(model_id="minimal-only")
        d = p.to_dict()
        assert d == {"model_id": "minimal-only"}
        assert len(d) == 1

    def test_agentfacts_extension_custom_key_format(self):
        """Custom extension keys with dots and hyphens are passed through."""
        p = ModelProvenance(model_id="test")
        result = p.to_agentfacts_extension(extension_key="x-vendor.custom-key")
        assert "x-vendor.custom-key" in result
        assert result["x-vendor.custom-key"]["model_id"] == "test"

    def test_decision_fields_never_includes_weights_hash(self):
        """to_decision_fields emits only model_id/model_version/provider_id."""
        p = ModelProvenance(
            model_id="check",
            model_version="1.0",
            provider_id="local",
            weights_hash="deadbeef",
            risk_level="high",
            model_type="base",
            base_model="llama",
            governance_tier="regulated",
        )
        fields = p.to_decision_fields()
        assert set(fields.keys()) <= {"model_id", "model_version", "provider_id"}
        assert "weights_hash" not in fields
        assert len(fields) == 3

    def test_from_dict_with_numeric_values_in_optional_fields(self):
        """from_dict with int model_version — stored as-is (no coercion)."""
        # from_dict passes values straight through via data.get(); no str cast
        p = ModelProvenance.from_dict({"model_id": "test", "model_version": 123})
        # The value is whatever was passed — Python dataclass doesn't enforce str
        assert p.model_version == 123  # type: ignore[comparison-overlap]

    def test_round_trip_preserves_all_fields(self):
        """Set all 8 fields, to_dict -> from_dict, verify equality."""
        original = ModelProvenance(
            model_id="rt-full",
            model_version="2.0",
            provider_id="azure",
            model_type="lora_adapter",
            base_model="llama-3.1-70b",
            governance_tier="regulated",
            weights_hash="sha256abc",
            risk_level="high",
        )
        rebuilt = ModelProvenance.from_dict(original.to_dict())
        assert rebuilt == original
