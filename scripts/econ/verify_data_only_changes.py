"""Fail-closed path policy for routine data-only publications.

This is a scope check, not approval of economic claims or of frontend changes.
Run it on the staged diff before committing and on the commit range before push.

Scope: the freeze covers exactly the active product renderers
(<product>/index.html for economic-calendar) via frontend_contract.json digests.
Landing pages such as home/index.html are deliberately outside the freeze. A frontend change is
accepted only when the same range carries the updated contract whose digest
binds the head bytes (re-checked here against the checkout); HTML without a
contract update, or HTML bundled with data, is rejected on both push and PR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

_DATE = r"\d{4}-\d{2}-\d{2}"
_POLICIES = {
    "economic-calendar": (
        re.compile(rf"economic-calendar/raw/{_DATE}/economic_calendar\.json\Z"),
        re.compile(r"economic-calendar/data/(?:latest|dates)\.json\Z"),
        re.compile(rf"economic-calendar/data/archive/{_DATE}\.json\Z"),
    ),
}


def validate_paths(paths: list[str], product: str) -> list[str]:
    """Return changed paths that cannot belong to a routine data-only update."""
    if product not in _POLICIES:
        raise ValueError(f"unsupported product: {product}")
    return [
        path for path in paths
        if (not path or path.startswith("/") or "\\" in path or ".." in path.split("/"))
        or not any(pattern.fullmatch(path) for pattern in _POLICIES[product])
    ]


def classify_changes(paths: list[str], event: str) -> list[str]:
    """Keep data, frontend, and maintenance changes in separate publication lanes."""
    if event not in {"push", "pull_request"}:
        raise ValueError("event must be push or pull_request")
    products = set(_POLICIES)
    data = [p for p in paths if p.split("/", 1)[0] in products and
            p.split("/", 1)[1].startswith(("data/", "raw/"))]
    frontends = [p for p in paths if p in {f"{product}/index.html" for product in products}]
    if data:
        owners = {p.split("/", 1)[0] for p in data}
        if len(owners) != 1:
            return ["a data release must contain exactly one product"]
        owner = owners.pop()
        return validate_paths(paths, owner)
    if frontends:
        if "scripts/econ/frontend_contract.json" not in paths:
            return ["frontend changes must update frontend_contract.json"]
    return []


def verify_template_binding(repo: Path, product: str) -> list[str]:
    """A data update is valid only against the separately frozen frontend bytes.

    Normalize line endings only: git-bash/Windows and Linux checkouts may differ
    in CRLF, while a renderer change must always require a new frontend review.
    """
    template = f"{product}/index.html"
    try:
        manifest = json.loads((repo / "scripts/econ/frontend_contract.json").read_text(encoding="utf-8"))
        expected = manifest[product]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            return [template]
        content = (repo / template).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() == expected:
            return []
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return [template]


def _git_paths(repo: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    lane = parser.add_mutually_exclusive_group(required=True)
    lane.add_argument("--product", choices=sorted(_POLICIES))
    lane.add_argument("--auto", action="store_true", help="classify a CI push or pull request")
    parser.add_argument("--event", choices=("push", "pull_request"), default="push")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--staged", action="store_true")
    source.add_argument("--working-tree", action="store_true")
    source.add_argument("--range", dest="commit_range", metavar="BASE..HEAD")
    args = parser.parse_args(argv)
    if args.staged:
        changed = _git_paths(args.repo, "diff", "--cached", "--name-only", "-z", "--no-renames")
    elif args.working_tree:
        changed = sorted(set(_git_paths(args.repo, "diff", "HEAD", "--name-only", "-z", "--no-renames")
                             + _git_paths(args.repo, "ls-files", "--others", "--exclude-standard", "-z")))
    else:
        if not re.fullmatch(r"[a-zA-Z0-9_./^-]+\.\.[a-zA-Z0-9_./^-]+", args.commit_range):
            parser.error("--range must be BASE..HEAD git revisions")
        changed = _git_paths(args.repo, "diff", "--name-only", "-z", "--no-renames", args.commit_range, "--")
    if args.auto:
        violations = classify_changes(changed, args.event)
        data_owners = {
            product for product in _POLICIES
            if any(not validate_paths([path], product) for path in changed)
        }
        frontend_owners = {
            product for product in _POLICIES if f"{product}/index.html" in changed
        }
        for product in data_owners | frontend_owners:
            violations += verify_template_binding(args.repo, product)
    else:
        violations = validate_paths(changed, args.product) + verify_template_binding(args.repo, args.product)
    if violations:
        print("DATA-ONLY SCOPE REJECTED: " + ", ".join(violations))
        return 1
    print(f"RELEASE SCOPE PASS: {args.product or 'classified'}; {len(changed)} changed paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
