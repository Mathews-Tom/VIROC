"""Unit tests for the cross-cutting compiler primitives in ``viroc.core``.

This is the M3 assertion surface: stable IDs, deterministic hashing, the
diagnostic model + registry + renderer, and the build context. Later milestones
emit specific diagnostic codes; here we only prove the primitives themselves.
"""

from __future__ import annotations

import pytest

from viroc.core.diagnostics import (
    Diagnostic,
    DiagnosticClass,
    Severity,
    Span,
    code,
    render,
    validate_code,
)
from viroc.core.hashing import canonical_json, hash_bytes, hash_data, hash_unordered
from viroc.core.ids import slugify, stable_id


class TestSlugify:
    def test_lowercases_and_underscores_separators(self) -> None:
        assert slugify("Vector DB") == "vector_db"

    def test_collapses_runs_of_separators(self) -> None:
        assert slugify("  Embedding   Model!! ") == "embedding_model"

    def test_strips_leading_and_trailing_separators(self) -> None:
        assert slugify("--documents--") == "documents"

    def test_is_idempotent(self) -> None:
        once = slugify("Retrieval-Augmented Generation")
        assert slugify(once) == once

    def test_preserves_existing_snake_case_identifier(self) -> None:
        assert slugify("vector_db") == "vector_db"

    @pytest.mark.parametrize("text", ["", "   ", "!!!", "---"])
    def test_unslugable_input_raises(self, text: str) -> None:
        with pytest.raises(ValueError, match="no slug-able characters"):
            slugify(text)


class TestStableId:
    def test_joins_slugified_parts_with_dots(self) -> None:
        assert stable_id("pipeline", "Vector DB", "box") == "pipeline.vector_db.box"

    def test_order_is_significant(self) -> None:
        assert stable_id("a", "b") != stable_id("b", "a")

    def test_is_deterministic(self) -> None:
        assert stable_id("scene", "Node 1") == stable_id("scene", "Node 1")

    def test_requires_at_least_one_part(self) -> None:
        with pytest.raises(ValueError, match="at least one part"):
            stable_id()

    def test_unslugable_part_raises(self) -> None:
        with pytest.raises(ValueError, match="no slug-able characters"):
            stable_id("scene", "!!!")

class TestHashing:
    def test_identical_input_hashes_identically(self) -> None:
        payload = {"id": "rag", "scenes": [1, 2, 3]}
        assert hash_data(payload) == hash_data(payload)

    def test_digest_is_prefixed_sha256_hex(self) -> None:
        digest = hash_bytes(b"")
        # sha256 of empty input, in the self-describing prefixed form.
        assert digest == (
            "sha256:e3b0c44298fc1c149afbf4c8996fb924"
            "27ae41e4649b934ca495991b7852b855"
        )

    def test_mapping_key_order_does_not_change_digest(self) -> None:
        assert hash_data({"a": 1, "b": 2}) == hash_data({"b": 2, "a": 1})

    def test_nested_mapping_key_order_does_not_change_digest(self) -> None:
        left = {"video": {"id": "x", "fps": 30}, "v": "0.1"}
        right = {"v": "0.1", "video": {"fps": 30, "id": "x"}}
        assert hash_data(left) == hash_data(right)

    def test_list_order_is_significant(self) -> None:
        assert hash_data([1, 2, 3]) != hash_data([3, 2, 1])

    def test_canonical_json_sorts_keys_and_omits_whitespace(self) -> None:
        assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'

    def test_unordered_is_order_independent(self) -> None:
        assert hash_unordered([3, 1, 2]) == hash_unordered([1, 2, 3])

    def test_unordered_preserves_multiplicity(self) -> None:
        assert hash_unordered([1, 1]) != hash_unordered([1])

    def test_unordered_hashes_mappings_by_value(self) -> None:
        a = {"path": "assets/doc.svg", "hash": "sha256:aa"}
        b = {"path": "assets/img.png", "hash": "sha256:bb"}
        assert hash_unordered([a, b]) == hash_unordered([b, a])

class TestCodeRegistry:
    def test_allocates_zero_padded_active_code(self) -> None:
        assert code(DiagnosticClass.SCHEMA, 2) == "VIR1002"
        assert code(DiagnosticClass.RENDERER, 31) == "VIR5031"

    @pytest.mark.parametrize(
        "cls", [DiagnosticClass.SEMANTIC, DiagnosticClass.OUTPUT]
    )
    def test_reserved_class_allocation_raises(self, cls: DiagnosticClass) -> None:
        with pytest.raises(ValueError, match="reserved in v1"):
            code(cls, 1)

    @pytest.mark.parametrize("number", [-1, 1000])
    def test_out_of_range_number_raises(self, number: int) -> None:
        with pytest.raises(ValueError, match="out of range"):
            code(DiagnosticClass.SCHEMA, number)

    def test_validate_accepts_active_codes(self) -> None:
        for value in ("VIR1002", "VIR2007", "VIR3001", "VIR4001", "VIR5031", "VIR7001"):
            validate_code(value)  # does not raise

    @pytest.mark.parametrize("value", ["VIR6001", "VIR8001"])
    def test_validate_rejects_reserved_codes(self, value: str) -> None:
        with pytest.raises(ValueError, match="reserved class"):
            validate_code(value)

    @pytest.mark.parametrize("value", ["VIR9001", "VIR10", "vir1002", "nope", "VIR1002x"])
    def test_validate_rejects_malformed_codes(self, value: str) -> None:
        with pytest.raises(ValueError, match="not a VIRxxxx code"):
            validate_code(value)


class TestDiagnosticModel:
    def test_construction_validates_code(self) -> None:
        with pytest.raises(ValueError, match="reserved class"):
            Diagnostic(code="VIR6001", message="nope")
        with pytest.raises(ValueError, match="not a VIRxxxx code"):
            Diagnostic(code="oops", message="nope")

    def test_defaults_to_error_severity(self) -> None:
        assert Diagnostic(code="VIR1002", message="x").severity is Severity.ERROR


# The compiler-grade diagnostic shape from overview §9.2. Carets align under the
# offending token at the span column; the locator/source/caret rows compose the
# framed block; the help line trails.
_VIR1002_RENDER = "\n".join(
    [
        'error[VIR1002]: unknown entity reference "vectorstore"',
        "  ┌─ rag-overview.vidir.yaml:31:13",
        "  │",
        "31│     - from: vectorstore",
        "  │             ^^^^^^^^^^^ not declared in entities",
        "  │",
        'help: did you mean "vector_db"?',
    ]
)


class TestRender:
    def _vir1002(self) -> Diagnostic:
        return Diagnostic(
            code="VIR1002",
            message='unknown entity reference "vectorstore"',
            span=Span(
                file="rag-overview.vidir.yaml",
                line=31,
                col=13,
                length=11,
                source="    - from: vectorstore",
                label="not declared in entities",
            ),
            help='did you mean "vector_db"?',
        )

    def test_matches_overview_9_2_snapshot(self) -> None:
        assert render(self._vir1002()) == _VIR1002_RENDER

    def test_reproduces_overview_9_2_shape(self) -> None:
        rendered = render(self._vir1002())
        assert rendered.startswith('error[VIR1002]: ')
        assert "┌─ rag-overview.vidir.yaml:31:13" in rendered
        assert "^^^^^^^^^^^ not declared in entities" in rendered
        assert rendered.endswith('help: did you mean "vector_db"?')

    def test_caret_aligns_under_span_column(self) -> None:
        rendered = render(self._vir1002()).splitlines()
        source_row = next(line for line in rendered if line.startswith("31│"))
        caret_row = next(line for line in rendered if "^" in line)
        assert source_row.index("vectorstore") == caret_row.index("^")

    def test_span_without_source_prints_locator_only(self) -> None:
        rendered = render(
            Diagnostic(
                code="VIR2007",
                message="overlapping beats",
                span=Span(file="s.vidir.yaml", line=5, col=3),
            )
        )
        assert "┌─ s.vidir.yaml:5:3" in rendered
        assert "^" not in rendered

    def test_no_span_renders_header_and_help_only(self) -> None:
        rendered = render(
            Diagnostic(
                code=code(DiagnosticClass.RENDERER, 31),
                message='renderer "manim" does not support primitive "html_embed"',
                help='use renderer "html", or provide a fallback image asset',
            )
        )
        assert rendered == (
            'error[VIR5031]: renderer "manim" does not support primitive "html_embed"\n'
            'help: use renderer "html", or provide a fallback image asset'
        )
