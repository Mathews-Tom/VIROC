"""Render post-validation: frame sampling and thresholded DCT pHash checks."""

from __future__ import annotations

import math
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from viroc.core import Diagnostic, DiagnosticClass, code

_FRAME_SIZE = 32
_HASH_SIZE = 8
_PIXELS_PER_FRAME = _FRAME_SIZE * _FRAME_SIZE
_PHASH_PREFIX = "phash:"

VIR_PERCEPTUAL_MISMATCH = code(DiagnosticClass.REPRODUCIBILITY, 4)

type GrayFrame = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class PerceptualComparison:
    """Threshold comparison for two frame-set perceptual hashes."""

    passed: bool
    distances: tuple[int, ...]
    threshold: int


def perceptual_hash_frame(frame: Sequence[Sequence[int]]) -> str:
    """Return the 64-bit DCT pHash for one grayscale frame as ``phash:<hex>``."""
    normalized = _resize_to_hash_frame(frame)
    coeffs = _dct_low_frequency(normalized)
    ac_values = [coeffs[row][col] for row in range(_HASH_SIZE) for col in range(_HASH_SIZE)]
    median = _median_without_dc(ac_values)
    bits = 0
    for value in ac_values:
        bits = (bits << 1) | int(value > median)
    return f"{_PHASH_PREFIX}{bits:016x}"


def perceptual_hash_frames(frames: Iterable[Sequence[Sequence[int]]]) -> str:
    """Return a deterministic frame-set pHash string from ordered sampled frames."""
    hashes = [perceptual_hash_frame(frame).removeprefix(_PHASH_PREFIX) for frame in frames]
    if not hashes:
        raise ValueError("at least one frame is required for perceptual hashing")
    return f"{_PHASH_PREFIX}{'-'.join(hashes)}"


def compare_perceptual_hashes(
    candidate: str, baseline: str, *, threshold: int
) -> PerceptualComparison:
    """Compare two frame-set pHashes with a per-frame Hamming threshold."""
    if threshold < 0:
        raise ValueError(f"threshold must be non-negative, got {threshold}")
    candidate_parts = _hash_parts(candidate)
    baseline_parts = _hash_parts(baseline)
    if len(candidate_parts) != len(baseline_parts):
        return PerceptualComparison(passed=False, distances=(), threshold=threshold)
    pairs = zip(candidate_parts, baseline_parts, strict=True)
    distances = tuple(_hamming_hex(left, right) for left, right in pairs)
    return PerceptualComparison(
        passed=all(distance <= threshold for distance in distances),
        distances=distances,
        threshold=threshold,
    )


def compare_frame_sets(
    candidate: Iterable[Sequence[Sequence[int]]],
    baseline: Iterable[Sequence[Sequence[int]]],
    *,
    threshold: int,
) -> PerceptualComparison:
    """Hash and compare two ordered sampled frame sets."""
    return compare_perceptual_hashes(
        perceptual_hash_frames(candidate),
        perceptual_hash_frames(baseline),
        threshold=threshold,
    )


def validate_perceptual_hash(
    candidate: str, baseline: str, *, threshold: int
) -> list[Diagnostic]:
    """Return a VIR7xxx diagnostic when render pHash exceeds the threshold."""
    comparison = compare_perceptual_hashes(candidate, baseline, threshold=threshold)
    if comparison.passed:
        return []
    distance_text = (
        ", ".join(str(distance) for distance in comparison.distances)
        or "frame count mismatch"
    )
    return [
        Diagnostic(
            code=VIR_PERCEPTUAL_MISMATCH,
            message="render perceptual hash differs from baseline",
            help=f"per-frame Hamming distances: {distance_text}; threshold: {threshold}",
        )
    ]


def sample_video_frames(
    video_path: Path,
    *,
    sample_count: int,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> list[GrayFrame]:
    """Sample ``sample_count`` evenly-spaced grayscale frames using FFmpeg."""
    if sample_count <= 0:
        raise ValueError(f"sample_count must be positive, got {sample_count}")
    duration = probe_duration_seconds(video_path, ffprobe=ffprobe)
    sample_rate = sample_count / duration
    command = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_rate:.12f},scale={_FRAME_SIZE}:{_FRAME_SIZE}:flags=lanczos,format=gray",
        "-frames:v",
        str(sample_count),
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    completed = subprocess.run(command, capture_output=True, check=False, timeout=120)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"ffmpeg frame sampling failed: {stderr}")
    return _raw_gray_frames(completed.stdout, sample_count)


def probe_duration_seconds(video_path: Path, *, ffprobe: str = "ffprobe") -> float:
    """Return container duration in seconds using ffprobe."""
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe duration probe failed: {completed.stderr.strip()}")
    duration = float(completed.stdout.strip())
    if duration <= 0:
        raise ValueError(f"video duration must be positive, got {duration}")
    return duration


def _raw_gray_frames(data: bytes, sample_count: int) -> list[GrayFrame]:
    frame_count = len(data) // _PIXELS_PER_FRAME
    if frame_count == 0:
        raise ValueError("ffmpeg returned no frame data")
    usable_count = min(sample_count, frame_count)
    frames: list[GrayFrame] = []
    for frame_index in range(usable_count):
        start = frame_index * _PIXELS_PER_FRAME
        frame_bytes = data[start : start + _PIXELS_PER_FRAME]
        rows = tuple(
            tuple(frame_bytes[row_start : row_start + _FRAME_SIZE])
            for row_start in range(0, _PIXELS_PER_FRAME, _FRAME_SIZE)
        )
        frames.append(rows)
    return frames


def _resize_to_hash_frame(frame: Sequence[Sequence[int]]) -> GrayFrame:
    if not frame:
        raise ValueError("frame must have at least one row")
    height = len(frame)
    width = len(frame[0])
    if width == 0:
        raise ValueError("frame rows must have at least one pixel")
    if any(len(row) != width for row in frame):
        raise ValueError("frame rows must all have the same width")
    rows: list[tuple[int, ...]] = []
    for y in range(_FRAME_SIZE):
        source_y = min(height - 1, y * height // _FRAME_SIZE)
        row: list[int] = []
        for x in range(_FRAME_SIZE):
            source_x = min(width - 1, x * width // _FRAME_SIZE)
            value = frame[source_y][source_x]
            if not 0 <= value <= 255:
                raise ValueError(f"grayscale pixel must be in [0, 255], got {value}")
            row.append(value)
        rows.append(tuple(row))
    return tuple(rows)


def _dct_low_frequency(frame: GrayFrame) -> tuple[tuple[float, ...], ...]:
    mean = sum(sum(row) for row in frame) / _PIXELS_PER_FRAME
    rows: list[tuple[float, ...]] = []
    for u in range(_HASH_SIZE):
        coeff_row: list[float] = []
        alpha_u = _alpha(u)
        for v in range(_HASH_SIZE):
            alpha_v = _alpha(v)
            total = 0.0
            for y, pixel_row in enumerate(frame):
                cos_y = math.cos((2 * y + 1) * u * math.pi / (2 * _FRAME_SIZE))
                for x, pixel in enumerate(pixel_row):
                    cos_x = math.cos((2 * x + 1) * v * math.pi / (2 * _FRAME_SIZE))
                    total += (pixel - mean) * cos_y * cos_x
            coeff_row.append(alpha_u * alpha_v * total)
        rows.append(tuple(coeff_row))
    return tuple(rows)


def _alpha(index: int) -> float:
    return math.sqrt(1 / _FRAME_SIZE) if index == 0 else math.sqrt(2 / _FRAME_SIZE)


def _median_without_dc(values: Sequence[float]) -> float:
    ordered = sorted(values[1:])
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _hash_parts(value: str) -> tuple[str, ...]:
    if not value.startswith(_PHASH_PREFIX):
        raise ValueError(f"perceptual hash must start with {_PHASH_PREFIX!r}")
    payload = value.removeprefix(_PHASH_PREFIX)
    if not payload:
        raise ValueError("perceptual hash payload cannot be empty")
    parts = tuple(payload.split("-"))
    for part in parts:
        if len(part) != 16:
            raise ValueError(f"frame pHash must be 16 hex chars, got {part!r}")
        int(part, 16)
    return parts


def _hamming_hex(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


__all__ = [
    "GrayFrame",
    "PerceptualComparison",
    "VIR_PERCEPTUAL_MISMATCH",
    "compare_frame_sets",
    "compare_perceptual_hashes",
    "perceptual_hash_frame",
    "perceptual_hash_frames",
    "probe_duration_seconds",
    "sample_video_frames",
    "validate_perceptual_hash",
]
