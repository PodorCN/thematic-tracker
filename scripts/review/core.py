"""Shared primitives for the independent-reviewer gate. Stdlib only.

Canonical form is pinned byte-identical to the former Node freezer
(JSON.stringify(doc, null, 2) + "\\n"): 2-space indent, UTF-8 raw
(ensure_ascii=False), trailing newline. Changing this function voids every
existing review, so it is pinned by tests/test_shared_reviewer.py against the
committed 2026-10-04 candidate bytes.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")

SCHEMA_VERSION = "1.0"
TOP_KEYS = (
    "schema_version", "reviewer", "operator", "reviewed_at", "snapshot_date",
    "candidate_sha256", "verdict", "executive_summary", "checks",
    "findings", "flags_dispositioned",
)
SEVERITIES = ("critical", "major", "minor")
DISPOSITIONS = ("fixed", "must_fix", "accepted", "next_cycle")
VERDICTS = ("APPROVED", "REVISE")
BANNED_IDENTITIES = {"self", "me", "operator", "reviewer", "ai", "agent", "opencode"}


def canonical(doc: object) -> bytes:
    return (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def toronto_today(now: _dt.datetime | None = None) -> str:
    now = now or _dt.datetime.now(tz=TORONTO)
    return now.astimezone(TORONTO).strftime("%Y-%m-%d")


def norm_identity(name: object) -> str:
    return str(name or "").strip().lower()
