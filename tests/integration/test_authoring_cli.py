"""Integration coverage for the ingest half of the M17 authoring CLI flow."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from viroc.authoring import authoring_brief_filename
from viroc.cli import main

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "authoring"


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    fixture_root = tmp_path / "tests" / "fixtures" / "authoring"
    fixture_root.mkdir(parents=True)
    shutil.copy2(_FIXTURES / "topic-brief.yaml", fixture_root / "topic-brief.yaml")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    shutil.copy2(_ROOT / "docs" / "overview.md", docs_dir / "overview.md")

    return fixture_root / "topic-brief.yaml", fixture_root / "happy-path-project"


@pytest.mark.integration
def test_ingest_command_appears_in_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ingest", "--help"]) == 0
    ingest_help = capsys.readouterr()
    assert "authoring-brief.yaml" in ingest_help.out
    assert ingest_help.err == ""


@pytest.mark.integration
def test_ingest_invalid_request_fails_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad_request = tmp_path / "bad-request.yaml"
    bad_request.write_text("source: [broken\n", encoding="utf-8")

    assert main(["ingest", str(bad_request)]) == 2
    captured = capsys.readouterr()
    assert "failed to load authoring request" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.integration
def test_ingest_writes_authoring_brief(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    request_path, project_path = _workspace(tmp_path)

    assert main(["ingest", str(request_path)]) == 0
    ingest_capture = capsys.readouterr()
    assert str(project_path / authoring_brief_filename()) in ingest_capture.out
    assert ingest_capture.err == ""
    assert (project_path / authoring_brief_filename()).exists()
