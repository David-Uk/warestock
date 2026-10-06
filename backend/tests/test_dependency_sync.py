"""Guard rails that keep the two dependency sources in lockstep.

``pyproject.toml`` is the editable-install source of truth; ``requirements.txt``
/ ``requirements-dev.txt`` are what CI and the Docker images install. The two
drifted once (the Prometheus instrumentator pin), which silently put CI on a
different starlette than the one the suite is validated against. These tests
fail the build the moment the files disagree again.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
_PIN = re.compile(r"^[A-Za-z0-9._-]+(\[[^\]]+\])?==[^\s]+$")


def _pyproject() -> dict:
    with (BACKEND / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _requirement_lines(filename: str) -> list[str]:
    """Return the pinned ``name==version`` entries of a requirements file."""
    entries: list[str] = []
    for raw in (BACKEND / filename).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-r", "--requirement")):
            continue
        entries.append(line)
    return entries


def _project() -> dict:
    return _pyproject()["project"]


def test_production_requirements_match_pyproject():
    declared = set(_project()["dependencies"])
    pinned = set(_requirement_lines("requirements.txt"))

    assert declared - pinned == set(), f"in pyproject only: {sorted(declared - pinned)}"
    assert pinned - declared == set(), f"in requirements.txt only: {sorted(pinned - declared)}"


def test_dev_requirements_match_pyproject():
    production = set(_project()["dependencies"])
    declared = set(_project()["optional-dependencies"]["dev"]) - production
    pinned = set(_requirement_lines("requirements-dev.txt"))

    assert declared - pinned == set(), f"in pyproject only: {sorted(declared - pinned)}"
    assert pinned - declared == set(), f"in requirements-dev.txt only: {sorted(pinned - declared)}"


def test_every_dependency_is_exactly_pinned():
    """CI must never resolve a range: unpinned or ``>=`` specs are rejected."""
    for filename in ("requirements.txt", "requirements-dev.txt"):
        for line in _requirement_lines(filename):
            assert _PIN.match(line), f"{filename}: '{line}' is not an exact pin"
