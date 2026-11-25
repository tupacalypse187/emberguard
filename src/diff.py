"""Unified diff parsing, file filtering, and hunk capping.

Diff hygiene keeps reviews cheap and relevant: lock files, vendored code,
and generated files are skipped, and oversized hunks are capped before
they ever reach the model.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

# Files that never get a security review.
SKIP_BASENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Gemfile.lock",
    "Cargo.lock",
    "composer.lock",
    "go.sum",
}
SKIP_DIR_PARTS = {"vendor", "node_modules", "dist", "build", ".git"}
SKIP_SUFFIXES = {".min.js", ".min.css", ".map", ".generated.py", ".pb.go"}

DEFAULT_MAX_HUNK_LINES = 200

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class DiffLine:
    kind: str   # "+", "-", or " " (context)
    text: str

    def render(self) -> str:
        return self.kind + self.text


@dataclass
class Hunk:
    header: str
    lines: list = field(default_factory=list)
    truncated: bool = False

    def render(self) -> str:
        return "\n".join([self.header] + [ln.render() for ln in self.lines])

    def added_lines(self) -> list:
        return [ln.text for ln in self.lines if ln.kind == "+"]

    def removed_lines(self) -> list:
        return [ln.text for ln in self.lines if ln.kind == "-"]


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    hunks: list = field(default_factory=list)
    is_binary: bool = False

    @property
    def path(self) -> str:
        return self.new_path or self.old_path

    def render(self) -> str:
        return "\n".join(h.render() for h in self.hunks)

    def added_text(self) -> str:
        return "\n".join(
            ln.text for h in self.hunks for ln in h.lines if ln.kind == "+"
        )

    def removed_text(self) -> str:
        return "\n".join(
            ln.text for h in self.hunks for ln in h.lines if ln.kind == "-"
        )


def _clean_path(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("a/") or raw.startswith("b/"):
        raw = raw[2:]
    return raw


def parse_diff(text: str) -> list:
    """Parse unified diff text into a list of FileDiff objects."""
    files = []
    current_file = None
    current_hunk = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" ")
            old = _clean_path(parts[2]) if len(parts) > 2 else ""
            new = _clean_path(parts[3]) if len(parts) > 3 else old
            current_file = FileDiff(old_path=old, new_path=new)
            files.append(current_file)
            current_hunk = None
            continue
        if current_file is None:
            continue
        if line.startswith("Binary files ") or line.startswith("GIT binary patch"):
            current_file.is_binary = True
            continue
        if line.startswith("--- "):
            current_file.old_path = _clean_path(line[4:])
            continue
        if line.startswith("+++ "):
            current_file.new_path = _clean_path(line[4:])
            continue
        if _HUNK_RE.match(line):
            current_hunk = Hunk(header=line)
            current_file.hunks.append(current_hunk)
            continue
        if current_hunk is not None and line[:1] in ("+", "-", " "):
            current_hunk.lines.append(DiffLine(kind=line[0], text=line[1:]))
    return [f for f in files if f.hunks or f.is_binary]


def should_skip(path: str) -> bool:
    """True when a file should be excluded from review."""
    if not path or path == "/dev/null":
        return True
    parts = set(path.replace("\\", "/").split("/"))
    if parts & SKIP_DIR_PARTS:
        return True
    base = os.path.basename(path)
    if base in SKIP_BASENAMES:
        return True
    return any(path.endswith(suffix) for suffix in SKIP_SUFFIXES)


def filter_files(files: list):
    """Split parsed files into (kept, skipped_paths). Binary files skip too."""
    kept, skipped = [], []
    for f in files:
        if f.is_binary or should_skip(f.path):
            skipped.append(f.path)
        else:
            kept.append(f)
    return kept, skipped


def cap_hunks(files: list, max_lines: int = DEFAULT_MAX_HUNK_LINES) -> list:
    """Truncate oversized hunks in place; oversized content is summarized
    by the reviewer prompt instead of being sent whole."""
    for f in files:
        for hunk in f.hunks:
            if len(hunk.lines) > max_lines:
                hunk.lines = hunk.lines[:max_lines]
                hunk.truncated = True
    return files


def prepare_diff(text: str, max_hunk_lines: int = DEFAULT_MAX_HUNK_LINES):
    """Full pipeline: parse, filter, cap. Returns (kept_files, skipped_paths)."""
    files = parse_diff(text)
    kept, skipped = filter_files(files)
    cap_hunks(kept, max_lines=max_hunk_lines)
    return kept, skipped
