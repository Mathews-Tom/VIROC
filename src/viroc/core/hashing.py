"""Deterministic content hashing.

The build manifest records ``source_hash`` and ``asset_hashes`` as a true
reproducibility key (overview §9.3, design §3.1): two machines running the same
VIROC version must compute the identical digest for the identical input. That
requires a *canonical* encoding, because Python ``dict`` iteration order and
JSON whitespace are otherwise free to vary.

Digests are returned as ``sha256:<hex>`` strings — the prefixed form used in the
manifest — so a digest is self-describing about its algorithm.

Order semantics:

- :func:`hash_data` canonicalizes with sorted object keys, so mapping key order
  never affects the digest. List order *is* significant: sequences are ordered
  data.
- :func:`hash_unordered` is for collections whose element order carries no
  meaning; reordering the input does not change the digest, while element
  multiplicity does (multiset semantics).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

_DIGEST_PREFIX = "sha256:"


def canonical_json(value: Any) -> str:
    """Encode a JSON-compatible ``value`` as canonical text.

    Object keys are sorted and separators are fixed with no insignificant
    whitespace, so the encoding depends only on the data, not on insertion order
    or formatting. Non-ASCII characters are preserved (``ensure_ascii=False``)
    and then UTF-8 encoded by the hashing functions.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_bytes(data: bytes) -> str:
    """Hash raw ``data`` into a ``sha256:<hex>`` digest string."""
    return f"{_DIGEST_PREFIX}{hashlib.sha256(data).hexdigest()}"


def hash_data(value: Any) -> str:
    """Hash a JSON-compatible ``value`` into a ``sha256:<hex>`` digest.

    Determinism: identical values hash identically across runs, and mapping key
    order does not affect the digest (the canonical encoding sorts keys). List
    order is preserved and therefore significant.
    """
    return hash_bytes(canonical_json(value).encode("utf-8"))


def hash_unordered(values: Iterable[Any]) -> str:
    """Hash a collection whose element order is not semantically meaningful.

    Each element is canonicalized, the canonical forms are sorted, and the sorted
    sequence is hashed. Reordering the input does not change the digest;
    duplicate elements still change it (multiset, not set).
    """
    return hash_data(sorted(canonical_json(value) for value in values))
