"""Fail-closed path policy for routine data-only publications.

This is a scope check, not approval of economic claims or of frontend changes.
Run it on the staged diff before committing and on the commit range before push.

Scope: the freeze covers exactly the active product renderers
(economic-calendar: index.html; Rates_decisions: index.html + app.js + styles.css)
via frontend_contract.json digests. Landing pages such as home/index.html are
deliberately outside the freeze. A frontend change is
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
_REVIEW_BUNDLE = r"(?:candidate\.json|candidate\.sha256|structural-flags\.json|pm-review\.json|review\.md)"
_POLICIES = {
    "economic-calendar": (
        re.compile(rf"economic-calendar/raw/{_DATE}/economic_calendar\.json\Z"),
        re.compile(r"economic-calendar/data/(?:latest|dates)\.json\Z"),
        re.compile(rf"economic-calendar/data/archive/{_DATE}\.json\Z"),
    ),
    "Rates_decisions": (
        re.compile(r"Rates_decisions/data/(?:current|latest|dates)\.json\Z"),
        re.compile(rf"Rates_decisions/data/archive/{_DATE}\.json\Z"),
        re.compile(rf"Rates_decisions/review/{_DATE}/{_REVIEW_BUNDLE}\Z"),
    ),
}

# Browser-served renderer files frozen per product. Manifest values may be a
# single sha256 string (legacy single-file products) or a {relpath: sha} dict.
_FRONTENDS = {
    "economic-calendar": ("index.html",),
    "Rates_decisions": ("index.html", "app.js", "styles.css"),
}
_FRONTEND_FILES = {
    f"{product}/{name}" for product, names in _FRONTENDS.items() for name in names
}


def _is_data_path(path: str) -> bool:
    """Exact allow-list: paths that may belong to a routine data-only update."""
    top = path.split("/", 1)[0] if "/" in path else ""
    return top in _POLICIES and any(rx.fullmatch(path) for rx in _POLICIES[top])


def _is_data_lane(path: str) -> bool:
    """Broad lane membership: decides data-release vs maintenance vs frontend.

    Deliberately wider than _is_data_path so unknown files in data lanes
    still trigger single-owner validation (fail-closed) instead of
    silently passing as maintenance.
    """
    if "/" not in path:
        return False
    top, rest = path.split("/", 1)
    if top not in _POLICIES:
        return False
    if top == "economic-calendar":
        return rest.startswith(("data/", "raw/"))
    if top == "Rates_decisions":
        return rest.startswith("data/") or bool(
            re.fullmatch(rf"review/{_DATE}/{_REVIEW_BUNDLE}", rest)
        )
    return False


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
    data = [p for p in paths if _is_data_lane(p)]
    frontends = [p for p in paths if p in _FRONTEND_FILES]
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
    Manifest values are either a single sha256 (legacy) or a {relpath: sha} dict.
    """
    try:
        manifest = json.loads((repo / "scripts/econ/frontend_contract.json").read_text(encoding="utf-8"))
        entry = manifest[product]
        if isinstance(entry, str):
            targets = {"index.html": entry}
        elif isinstance(entry, dict):
            targets = entry
        else:
            return [f"{product}/{name}" for name in _FRONTENDS.get(product, ("index.html",))]
        bad = []
        for relpath, expected in targets.items():
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                bad.append(f"{product}/{relpath}")
                continue
            try:
                content = (repo / product / relpath).read_bytes().replace(b"\r\n", b"\n")
            except OSError:
                bad.append(f"{product}/{relpath}")
                continue
            if hashlib.sha256(content).hexdigest() != expected:
                bad.append(f"{product}/{relpath}")
        return bad
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return [f"{product}/{name}" for name in _FRONTENDS.get(product, ("index.html",))]


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
            product for product in _POLICIES
            if any(f"{product}/{name}" in changed for name in _FRONTENDS[product])
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
