"""Unit tests for the cross-cutting compiler primitives in ``viroc.core``.

This is the M3 assertion surface: stable IDs, deterministic hashing, the
diagnostic model + registry + renderer, and the build context. Later milestones
emit specific diagnostic codes; here we only prove the primitives themselves.
"""

from __future__ import annotations

import pytest

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
