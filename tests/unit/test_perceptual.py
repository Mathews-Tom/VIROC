"""Perceptual render post-validation without invoking a renderer."""

from __future__ import annotations

from viroc.compiler.postvalidate import (
    VIR_PERCEPTUAL_MISMATCH,
    compare_frame_sets,
    compare_perceptual_hashes,
    perceptual_hash_frames,
    validate_perceptual_hash,
)


def _gradient_frame(offset: int = 0) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(x * 3 + y * 2 + offset for x in range(32)) for y in range(32))


def _checkerboard_frame() -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(255 if (x + y) % 2 == 0 else 0 for x in range(32)) for y in range(32))


def test_frame_set_phash_is_stable_for_identical_frames() -> None:
    frames = [_gradient_frame(), _gradient_frame(12)]

    first = perceptual_hash_frames(frames)
    second = perceptual_hash_frames(frames)

    assert first == second
    assert first.startswith("phash:")


def test_phash_comparator_passes_near_identical_frame_sets() -> None:
    baseline = [_gradient_frame(), _gradient_frame(12)]
    candidate = [_gradient_frame(1), _gradient_frame(13)]

    comparison = compare_frame_sets(candidate, baseline, threshold=4)

    assert comparison.passed
    assert comparison.distances
    assert max(comparison.distances) <= 4


def test_phash_comparator_fails_beyond_threshold() -> None:
    baseline = perceptual_hash_frames([_gradient_frame(), _gradient_frame(12)])
    candidate = perceptual_hash_frames([_checkerboard_frame(), _checkerboard_frame()])

    comparison = compare_perceptual_hashes(candidate, baseline, threshold=4)

    assert not comparison.passed
    assert max(comparison.distances) > 4


def test_validate_perceptual_hash_returns_vir7xxx_on_mismatch() -> None:
    baseline = perceptual_hash_frames([_gradient_frame()])
    candidate = perceptual_hash_frames([_checkerboard_frame()])

    diagnostics = validate_perceptual_hash(candidate, baseline, threshold=4)

    assert [diagnostic.code for diagnostic in diagnostics] == [VIR_PERCEPTUAL_MISMATCH]
    assert diagnostics[0].code == "VIR7004"
