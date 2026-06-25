"""Semantic IR parsing and pre-validation (M4).

Grows across the M4 stack: PR-1 covers the models (the ``from`` alias
round-trip); later PRs add IO/fixture parsing and the VIR1xxx pre-validation
cases.
"""

from __future__ import annotations

from viroc.ir import Edge


def test_edge_from_alias_round_trips() -> None:
    """``from`` (a keyword) is authored as the alias and survives a round-trip."""
    edge = Edge.model_validate({"from": "documents", "to": "chunks", "kind": "split"})
    assert edge.from_ == "documents"
    assert edge.to == "chunks"

    dumped = edge.model_dump(by_alias=True)
    assert dumped["from"] == "documents"
    assert "from_" not in dumped

    assert Edge.model_validate(dumped) == edge


def test_edge_populates_by_field_name() -> None:
    """``populate_by_name`` accepts the Python field name as well as the alias."""
    by_name = Edge.model_validate({"from_": "a", "to": "b"})
    by_alias = Edge.model_validate({"from": "a", "to": "b"})
    assert by_name == by_alias
    assert by_name.kind == "flow"
