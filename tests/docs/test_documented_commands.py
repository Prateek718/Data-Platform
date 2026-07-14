"""Every `data-platform-*` command the docs promise must actually exist.

Documentation drift on commands is the defect a packaging stage leaves behind: the entry points move
or get renamed, the docs keep telling a stranger to run something that is not there, and the first
thing they try fails. The README is the front door — a command in it is a promise.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = ("README.md", "REPRODUCIBILITY.md")

# A command as the docs write it: `data-platform-mcp`, in prose or in a shell block.
COMMAND = re.compile(r"\bdata-platform-[a-z][a-z0-9-]*")


def declared_scripts() -> set[str]:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return set(pyproject["project"]["scripts"])


def documented_commands() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for doc in DOCS:
        text = (REPO_ROOT / doc).read_text(encoding="utf-8")
        for command in COMMAND.findall(text):
            found.setdefault(command, set()).add(doc)
    return found


def test_the_docs_document_at_least_the_commands_a_reader_needs() -> None:
    """A guard against the opposite drift: the docs quietly losing the commands entirely."""
    documented = documented_commands()
    assert {"data-platform-bootstrap", "data-platform-mcp"} <= set(documented), (
        "the README must tell a stranger how to fetch the data and serve it"
    )


@pytest.mark.parametrize("command", sorted(documented_commands()))
def test_every_documented_command_exists(command: str) -> None:
    scripts = declared_scripts()
    where = ", ".join(sorted(documented_commands()[command]))
    assert command in scripts, (
        f"{where} documents `{command}`, but pyproject declares no such console script "
        f"(declared: {', '.join(sorted(scripts))}). A command in the docs is a promise."
    )
