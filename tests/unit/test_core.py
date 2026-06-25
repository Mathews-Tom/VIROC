"""Unit tests for the cross-cutting compiler primitives in ``viroc.core``.

This is the M3 assertion surface: stable IDs, deterministic hashing, the
diagnostic model + registry + renderer, and the build context. Later milestones
emit specific diagnostic codes; here we only prove the primitives themselves.
"""

from __future__ import annotations

import pytest

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
