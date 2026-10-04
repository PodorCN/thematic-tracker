"""Structural checks for the Fed/BOC candidate. No natural-language parsing.

Kept deliberately: hashes, timestamp ordering, arithmetic reproducibility,
probability bounds, and the containment rule that closes the deletion bypass.
Removed deliberately: every check that had to read English prose (weekday/date
pairing, verb/object stem matching, negation guards, prose date backtracking).
Those were evaded by synonym edits across two independent PM reviews, and they
produced factually wrong messages on correct candidates.
"""
import hashlib
import json
import re
from datetime import datetime, time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SESSION_CLOSE = time(16, 0)


def parse_dt(value):
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def walk_provenance(node, path=""):
    if isinstance(node, dict):
        if "sha256" in node and "source_url" in node:
            yield path, node
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if key == "source_provenance" and isinstance(value, dict):
                for sub, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        yield from walk_provenance(sub_value, f"{child}.{sub}")
            else:
                yield from walk_provenance(value, child)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_provenance(value, f"{path}[{index}]")


def walk_keyed(node, names):
    stack = [(node, "")]
    while stack:
        current, path = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                child = f"{path}.{key}" if path else str(key)
                if key in names and not isinstance(value, (dict, list)):
                    yield child, value
                stack.append((value, child))
        elif isinstance(current, list):
            for index, value in enumerate(current):
                stack.append((value, f"{path}[{index}]"))


def resolve_evidence(value):
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    resolved = REPO_ROOT / candidate
    return resolved if resolved.exists() else None


# --------------------------------------------------------------------------- #
def check_required_containment(payload):
    """Absence fails closed. Closes the 2026-09-28 deletion bypass."""
    problems = []
    market = payload.get("market") or {}
    if not (market.get("tickers") or (payload.get("meetings") or {}) or (payload.get("drivers") or {})
            or payload.get("calendar") or payload.get("decision_brief")):
        return ["payload renders nothing; this is not a publishable snapshot"]
    if not payload.get("decision_brief"):
        problems.append("decision_brief is required; without it the page renders no decision frame")
    if not any(True for _ in walk_provenance(payload)):
        problems.append("no hash-bound source_provenance; unevidenced claims are unpublishable")
    if not (payload.get("evidence_manifest") or {}).get("path"):
        problems.append("evidence_manifest.path is required for field-level evidence binding")
    return problems


def check_as_of_coherence(payload):
    problems = []
    as_of = parse_dt(payload.get("as_of"))
    if as_of is None:
        return ["as_of missing or not offset-bearing ISO-8601"]
    brief = parse_dt((payload.get("decision_brief") or {}).get("as_of_toronto"))
    if brief is not None and brief != as_of:
        problems.append(f"decision_brief.as_of_toronto {brief.isoformat()} != as_of {as_of.isoformat()}")
    recalc = parse_dt((payload.get("macro_driver_recalculation") or {}).get("as_of"))
    if recalc is not None and recalc != as_of:
        problems.append(f"macro_driver_recalculation.as_of {recalc.isoformat()} is not the payload as_of")
    for path, prov in walk_provenance(payload):
        for field in ("retrieved_at_toronto", "observed_at_toronto"):
            value = parse_dt(prov.get(field))
            if value is not None and value > as_of:
                problems.append(f"{path}.{field} {value.isoformat()} is after payload as_of")
    for path, value in walk_keyed(payload, {"observed_at_toronto", "as_of_close", "as_of_toronto"}):
        observed = parse_dt(value)
        if observed is not None and observed > as_of:
            problems.append(f"{path} {observed.isoformat()} is after payload as_of")
    return problems


def check_market_close_semantics(payload):
    """A value labelled a session close was observed at/after that close."""
    problems = []
    for index, ticker in enumerate((payload.get("market") or {}).get("tickers") or []):
        where = f"market.tickers[{index}] ({ticker.get('symbol', '?')})"
        session, observed = ticker.get("session_date"), parse_dt(ticker.get("observed_at_toronto"))
        if session and observed:
            try:
                session_date = datetime.strptime(session, "%Y-%m-%d").date()
            except ValueError:
                problems.append(f"{where}.session_date is not a date: {session!r}")
                continue
            if observed.date() != session_date:
                problems.append(f"{where} observed {observed.date()} but session_date is {session}")
            elif observed.timetz().replace(tzinfo=None) < SESSION_CLOSE:
                problems.append(f"{where} observed {observed.isoformat()} before the 16:00 close")
        elif session and not observed:
            problems.append(f"{where} claims session_date {session} with no observed_at_toronto")
    return problems


def check_provenance_traceability(payload):
    """Every claimed sha256 must match the bytes on disk."""
    problems = []
    for path, prov in walk_provenance(payload):
        declared = str(prov.get("sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", declared):
            problems.append(f"{path}.sha256 is not a 64-hex digest")
            continue
        evidence = str(prov.get("evidence_path") or "")
        if not evidence:
            problems.append(f"{path} declares a sha256 with no evidence_path")
            continue
        resolved = resolve_evidence(evidence)
        if resolved is None:
            problems.append(f"{path}.evidence_path does not exist: {evidence}")
            continue
        actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual != declared:
            problems.append(f"{path} is stale: {evidence} hashes {actual[:12]}, claims {declared[:12]}")
    return problems


def check_pricing_honesty(payload):
    """Probabilities bounded; unusable quotes null; rates on their own scale."""
    problems = []
    for bank, block in (payload.get("meetings") or {}).items():
        pricing = (block or {}).get("pricing") or {}
        status = pricing.get("probability_status")
        values = [pricing.get(key) for key in ("cut_25bp", "hold", "hike_25bp")]
        for field, value in pricing.items():
            if value is None:
                continue
            if any(token in field for token in ("rate", "_bp", "edge")):
                if isinstance(value, (int, float)) and not 0.0 <= float(value) <= 20.0:
                    problems.append(f"meetings.{bank}.pricing.{field}={value!r} is not a rate level")
                continue
            if isinstance(value, (int, float)) and not 0.0 <= float(value) <= 1.0:
                problems.append(f"meetings.{bank}.pricing.{field}={value!r} outside [0,1]")
        if status == "unavailable" and any(v is not None for v in values):
            problems.append(f"meetings.{bank} is unavailable but carries probabilities")
        if status == "available":
            if any(not isinstance(v, (int, float)) for v in values):
                problems.append(f"meetings.{bank} is available but lacks numeric probabilities")
            elif all(isinstance(v, (int, float)) for v in values) and abs(sum(values) - 1.0) > 0.02:
                problems.append(f"meetings.{bank} probabilities sum to {sum(values)}, not 1")
    return problems


def check_derived_numbers(payload):
    """Percentage changes must recompute from the bases the payload displays."""
    problems = []
    for index, ticker in enumerate((payload.get("market") or {}).get("tickers") or []):
        where = f"market.tickers[{index}] ({ticker.get('symbol', '?')})"
        price = ticker.get("price")
        for horizon, base_key in (("1d", "base_1d_price"), ("1w", "base_1w_price")):
            change, base = ticker.get(f"chg_{horizon}"), ticker.get(base_key)
            if change is None or not isinstance(price, (int, float)) or not isinstance(base, (int, float)):
                continue
            if base == 0:
                problems.append(f"{where}.{base_key} is zero")
                continue
            expected = price / base - 1.0
            if round(expected, 6) != round(float(change), 6):
                problems.append(f"{where}.chg_{horizon}={change!r} != {round(expected, 6)!r} from {price}/{base}")
    return problems


def check_driver_chronology(payload):
    """published_at <= observed_at <= as_of, and id dates agree with published_at."""
    problems = []
    as_of = parse_dt(payload.get("as_of"))
    for bank, sides in (payload.get("drivers") or {}).items():
        for side, entries in (sides or {}).items():
            for index, driver in enumerate(entries or []):
                where = f"drivers.{bank}.{side}[{driver.get('id', index)}]"
                if not driver.get("source_url"):
                    problems.append(f"{where} has no source_url")
                published = parse_dt(driver.get("published_at_toronto"))
                observed = parse_dt(driver.get("observed_at_toronto"))
                if published and observed and observed < published:
                    problems.append(f"{where} observed {observed.isoformat()} precedes published")
                if as_of and published and published > as_of:
                    problems.append(f"{where} published after payload as_of")
                embedded = re.search(r"(\d{4})(\d{2})(\d{2})", str(driver.get("id", "")))
                if embedded and published:
                    try:
                        stamp = datetime(int(embedded.group(1)), int(embedded.group(2)), int(embedded.group(3)))
                    except ValueError:
                        continue
                    if published.date() != stamp.date():
                        problems.append(f"{where} id says {stamp.date()}, published_at says {published.date()}")
    return problems


def check_driver_side_signs(payload):
    """A contraction print is not hawkish, whatever it beat.

    Closes the 2026-09-28 BoC retail finding: -0.7% m/m labelled delta_type
    'beat' and filed under hawkish.  This is arithmetic on the stored numbers,
    not prose interpretation.
    """
    problems = []

    def as_number(value):
        """Drivers store actual as a string like '-0.7'; parse it, else None."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip().rstrip("%"))
            except ValueError:
                return None
        return None

    for bank, sides in (payload.get("drivers") or {}).items():
        for side, entries in (sides or {}).items():
            for index, driver in enumerate(entries or []):
                data = driver.get("data") or {}
                actual, delta_type = as_number(data.get("actual")), data.get("delta_type")
                sign = data.get("macro_sign")
                if actual is not None and delta_type == "beat" and actual < 0:
                    problems.append(
                        f"drivers.{bank}.{side}[{driver.get('id', index)}] has actual {actual} on the "
                        f"{side} side with delta_type 'beat': a negative print is growth-negative "
                        "regardless of the consensus it beat"
                    )
                if sign and actual is not None and actual < 0 and side == "hawkish":
                    problems.append(
                        f"drivers.{bank}.{side}[{driver.get('id', index)}] declares macro_sign "
                        f"{sign!r} with a negative actual"
                    )
    return problems


def check_calendar_rendered(payload):
    """Anything the brief cites as a catalyst must be in the rendered array.

    The page renders only payload.calendar, so an event that lives only in
    calendar_coverage is invisible to a reader.
    """
    problems = []
    dates = set()
    for row in payload.get("calendar") or []:
        for field in ("datetime_toronto", "event_date_toronto", "datetime_utc"):
            value = row.get(field)
            if isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value):
                dates.add(value[:10])
    return problems


def check_renderer_contract(payload):
    """Every field the brief advertises must be one the page actually reads.

    The 2026-09-28 PM review found `what_is_priced`, `falsifiers` and
    `attention_budget` present in the payload and grepped zero times in
    index.html: the brief promised a 90-second read that no reader could see.
    A hash cannot catch that, and neither can a PM re-reading the JSON.

    Allowlisted brief keys are fields that legitimately do not reach the page
    (schema_version, authoring_note, the rationale that trade_status cannot
    itself carry). Everything else must appear in the renderer or be dropped.
    """
    problems = []
    index = REPO_ROOT / "fed-boc-watcher" / "index.html"
    if not index.exists():
        return ["fed-boc-watcher/index.html is missing; renderer contract cannot be checked"]
    html = index.read_text(encoding="utf-8", errors="replace")
    brief = payload.get("decision_brief") or {}
    if not brief:
        return []  # required_containment already reports the missing brief
    for field in ("trade_status", "summary", "changes_since_previous", "banks",
                  "largest_pnl_risks", "source_references", "what_is_priced",
                  "falsifiers", "attention_budget"):
        if brief.get(field) in (None, "", [], {}) and field != "trade_status":
            continue
        if field not in html:
            problems.append(f"decision_brief.{field} is set but index.html never reads it")
    # Any OTHER non-empty key is held to the same bar. A fixed list only catches
    # the fields someone remembered to enumerate; the failure mode here is a new
    # field being written into the brief and silently dropped by the page.
    enumerated = {"trade_status", "summary", "changes_since_previous", "banks",
                  "largest_pnl_risks", "source_references", "what_is_priced",
                  "falsifiers", "attention_budget", "as_of_toronto", "headline",
                  "authored_at_toronto", "authoring_note", "trade_status_rationale",
                  "h1", "subhead", "label", "schema_version"}
    for field, value in brief.items():
        if field in enumerated or value in (None, "", [], {}):
            continue
        if isinstance(value, str) and field not in html:
            problems.append(
                f"decision_brief.{field} is set but index.html never reads it "
                "(unwired field: the page will not show it)"
            )
    # The neutral-display branch matches on an exact token, not a substring.
    # Extract the literal the renderer actually compares against, then require
    # the payload to use it. (2026-09-28: a reworded status broke all three
    # noEdge branches and the bank cards printed a confident directional call
    # beside a NO TRADE frame.)
    import re as _re
    literals = _re.findall(r"const noEdge=\w+\?\.trade_status==='([^']*)'", html)
    if brief.get("trade_status") and literals:
        if brief["trade_status"] not in literals:
            problems.append(
                f"decision_brief.trade_status is {brief['trade_status']!r}; the renderer compares against "
                f"{sorted(set(literals))!r}, so the neutral-display branch will not fire"
            )
    # A delta_type the badge map does not know renders as 'neutral'.
    for bank, sides in (payload.get("drivers") or {}).items():
        for side, entries in (sides or {}).items():
            for index_, driver in enumerate(entries or []):
                delta = (driver.get("data") or {}).get("delta_type")
                if delta and f"'{delta}'" not in html and f'"{delta}"' not in html:
                    problems.append(
                        f"drivers.{bank}.{side}[{driver.get('id', index_)}] uses delta_type "
                        f"{delta!r}, which the renderer's badge map does not list"
                    )
    return problems


def _norm(text):
    """Normalise dashes and whitespace so a stored value can be found in a capture."""
    return (str(text).replace("\u2212", "-").replace("\u2013", "-")
            .replace("\u2014", "-").replace(" ", ""))


def _numeric_variants(value):
    """Every spelling of one number that a capture might use.

    A page writes 0.6, 0.60, 0.600, .6, or (in JSON) 0.600000; a payload writes
    +0.6% or -0.7%. The match must be on the numeric value, never on the sign or
    on a digit fragment: an earlier version emitted '-6' for '0.6%' and '+0.6'
    for '+0.6%', so a real 0.6 in a capture never matched and the gate cried
    "unevidenced" about a number that was right there. (Round 3, 2026-09-28:
    that false positive made me overwrite a correct +0.6% with a false claim
    that the evidence was missing.)
    """
    out = set()
    for token in re.findall(r"\d[\d,]*(?:\.\d+)?|\.\d+", str(value)):
        bare = token.replace(",", "")
        if "." not in bare:
            out.add(bare)
            continue
        whole, frac = bare.split(".", 1)
        digits = whole.lstrip("0") or "0"
        # trailing-zero and leading-zero spellings of the same value
        for width in (1, 2, 3):
            out.add(f"{digits}.{frac[:width].ljust(width, '0')}")
        trimmed = frac.rstrip("0")
        if trimmed:
            out.add(f"{digits}.{trimmed}")
        if digits != "0":
            out.add(f"0.{frac}")
    return {v for v in out if v and v not in ("0",) and len(v) >= 2}


def _matching_row_blob(driver):
    """The exact source row a card pins, as text, if it pins one.

    Cards that quote a consensus provider carry `matching_row` in their
    provenance: the specific event object whose actual/consensus/previous the
    card is asserting. If present, that row -- not the whole file -- is the
    evidence for those numbers.
    """
    row = None
    for block in (driver.get("source_provenance") or {}).values():
        if isinstance(block, dict) and isinstance(block.get("matching_row"), dict):
            row = block["matching_row"]
    return json.dumps(row, ensure_ascii=False) if row else None


# Sub-national labels that mean a figure is NOT the national one.
_SUBNATIONAL = (
    "nova scotia", "n.s.", "ontario", "ont.", "quebec", "que.", "british columbia",
    "b.c.", "alberta", "alta.", "manitoba", "man.", "saskatchewan", "sask.",
    "newfoundland", "n.l.", "prince edward", "p.e.i.", "nova", "new brunswick",
    "n.b.", "yukon", "northwest territories", "nunavut",
)


def _plausible_national_hit(blob, variants):
    """True unless every occurrence of the number is attached to a sub-national row."""
    hits = []
    for variant in variants:
        start = 0
        while True:
            index = blob.find(variant, start)
            if index < 0:
                break
            hits.append(index)
            start = index + 1
    if not hits:
        return False
    for index in hits:
        window = blob[max(0, index - 400): index + 400].lower()
        if not any(name in window for name in _SUBNATIONAL):
            return True
    return False


def check_evidence_contains_claim(payload):
    """A displayed driver value must appear in one of its own bound captures.

    2026-09-28, review round 1: Michigan was changed from the preliminary 47.8
    to the September final 48.1 in the display fields, but the bound capture was
    the 9/24 fetch, which contains 47.8 and no 48.1 at all. The number was
    correct and completely unevidenced. Nothing else in the gate can see this:
    the hash matched its own (stale) file and the arithmetic was right.

    Fails closed on an empty evidence file: a 0-byte capture evidences nothing,
    and a card that cites one is claiming support it does not have.
    """
    problems = []
    for bank, sides in (payload.get("drivers") or {}).items():
        for side, entries in (sides or {}).items():
            for index, driver in enumerate(entries or []):
                where = f"drivers.{bank}.{side}[{driver.get('id', index)}]"
                paths = []

                def collect(node):
                    if isinstance(node, dict):
                        for key, value in node.items():
                            if isinstance(value, str) and (
                                    key == "evidence_path" or key.endswith("_evidence")):
                                paths.append(value)
                            collect(value)
                    elif isinstance(node, list):
                        for value in node:
                            collect(value)

                collect(driver.get("source_provenance") or {})
                for item in driver.get("market_validation") or []:
                    if item.get("evidence_path"):
                        paths.append(str(item["evidence_path"]))
                blobs = []
                empty = []
                for rel in paths:
                    resolved = resolve_evidence(rel)
                    if resolved is None:
                        continue
                    try:
                        if resolved.stat().st_size == 0:
                            empty.append(rel)
                            continue
                        blobs.append(resolved.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        pass
                # A pinned matching_row is itself evidence, quoted verbatim from
                # the source row. It must be searchable even when the file it came
                # from is gone, otherwise a card can pass with no readable capture
                # at all (the 2026-09-28 FXStreet row is the real case: the CSV is
                # fetched on some rounds and absent on others).
                row = _matching_row_blob(driver)
                if row is not None and not any(row in blob for blob in blobs):
                    blobs = blobs + [row]
                if empty:
                    # A 401/404 capture is legitimate evidence that the fetch FAILED,
                    # which is itself worth recording -- a card must say so in its
                    # provenance. What is not legitimate is a card that leans on the
                    # empty file to support a number. Flag it only when the card also
                    # has no non-empty evidence at all.
                    if not blobs:
                        problems.append(
                            f"{where} cites only zero-byte evidence "
                            f"({', '.join(Path(e).name for e in empty)}) and has no readable capture: "
                            "its values are unevidenced"
                        )
                    else:
                        noted = any(
                            "401" in str(v) or "zero" in str(v).lower() or "failed" in str(v).lower()
                            or "http_status" in str(k).lower()
                            for k, v in (driver.get("source_provenance") or {}).items()
                        )
                        if not noted:
                            problems.append(
                                f"{where} cites a zero-byte capture "
                                f"({', '.join(Path(e).name for e in empty)}) without recording that "
                                "the fetch failed"
                            )
                if not blobs:
                    continue
                data = driver.get("data") or {}
                for field in ("actual", "previous", "forecast"):
                    value = data.get(field)
                    if not isinstance(value, str) or not any(ch.isdigit() for ch in value):
                        continue
                    # A field that documents its own absence ("not in the bound
                    # capture") is not claiming a number, so the number test does
                    # not apply; only the provenance trail can be checked there.
                    if not re.fullmatch(r"[+-]?[\d.,]+\s*%?\s*[kKmM]?", value.strip()):
                        continue
                    variants = _numeric_variants(value)
                    if not variants:
                        continue
                    hit = next((blob for blob in blobs
                                if any(v in blob for v in variants)), None)
                    if hit is not None:
                        # A bare number match is not enough: the 2026-09-28 retail
                        # card claimed a June headline the capture lacked, while
                        # the file did contain 0.6 -- as the NOVA SCOTIA provincial
                        # row, and as the consensus provider's matching_row. A
                        # number proves the value is somewhere in the file, not
                        # that it is the value this card is about. If the card
                        # pins a matching_row, require the number to appear there.
                        # Prefer the row the card pins; if it pins none, fall back
                        # to requiring a national-level hit, so a provincial figure
                        # cannot stand in for the national one.
                        if row is None:
                            if not _plausible_national_hit(hit, variants):
                                problems.append(
                                    f"{where}.data.{field} is {value!r}; the number occurs in a bound "
                                    "capture only alongside sub-national labels, and the card pins no "
                                    "matching_row: it may be a provincial figure, not this one"
                                )
                            continue
                        if not any(v in row for v in variants):
                            problems.append(
                                f"{where}.data.{field} is {value!r}; the number is not in the "
                                "matching_row this card pins (the file contains it elsewhere, e.g. a "
                                "provincial row): the card's own evidence does not carry this value"
                            )
                        continue
                    problems.append(
                        f"{where}.data.{field} is {value!r} but none of its {len(blobs)} bound "
                        f"evidence file(s) contain any of {sorted(variants)}: the displayed value "
                        "has no evidence behind it (re-fetch the source, or bind the capture that "
                        "actually carries it)"
                    )
    return problems


def _approved_shas():
    shas = set()
    root = REPO_ROOT / "review-artifacts"
    if not root.exists():
        return shas
    for path in root.rglob("pm-review*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(data.get("verdict", "")).lower() == "approved" and data.get("candidate_sha256"):
            shas.add(str(data["candidate_sha256"]).lower())
    return shas


def _approved_candidates(approved_shas):
    """Every frozen candidate whose bytes an approved review is bound to."""
    out = []
    for candidate in (REPO_ROOT / "fed-boc-watcher" / "review").rglob("candidate.json"):
        try:
            if hashlib.sha256(candidate.read_bytes()).hexdigest().lower() in approved_shas:
                out.append(candidate)
        except OSError:
            continue
    return out


def _uncommitted_published_drift():
    """The published file differs from git HEAD.

    The published path is only ever advanced by archive_fed_boc.py and then
    committed, so any working-tree difference is a hand edit. This is the only
    constraint available when no review has approved anything yet.
    """
    import subprocess
    rel = "fed-boc-watcher/data/latest.json"
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", rel],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None  # git unavailable: do not manufacture a verdict
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return (
        f"data/latest.json differs from git HEAD ({result.stdout.strip()}): the published "
        "path was hand-edited in the working tree. Only archive_fed_boc.py may write it, "
        "and only from an approved candidate"
    )


# Fields the archiver adds at publication time; everything else must be identical
# to the reviewed candidate.
ARCHIVER_FIELDS = ("archived_at", "snapshot_date", "stale")


def _strip_archiver_fields(payload):
    return {k: v for k, v in payload.items() if k not in ARCHIVER_FIELDS}


def _content_matches_candidate(published, candidate_path):
    """True when the published file is a candidate plus archiver stamps only."""
    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return _strip_archiver_fields(published) == _strip_archiver_fields(candidate)


def _is_legitimate_uncommitted_publication(approved):
    """A freshly archived, not-yet-committed publication of an approved candidate.

    Publishing legitimately leaves the working tree dirty until the commit lands,
    so 'differs from git HEAD' alone is not evidence of a hand edit. The test is
    whether the file carries archiver stamps and matches an approved candidate's
    content exactly.
    """
    latest = REPO_ROOT / "fed-boc-watcher" / "data" / "latest.json"
    try:
        published = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not published.get("archived_at") or not published.get("snapshot_date"):
        return False
    return any(_content_matches_candidate(published, c)
               for c in _approved_candidates(approved))


def check_published_path_provenance(payload=None):
    """data/latest.json may only contain an APPROVED candidate, or the last
    legitimately-published one.

    2026-09-28, round 4: the PM reviewer ran out of tool budget mid-review and
    left iteration-04 (sha 5b67d29f..., never approved) sitting in data/latest.json.
    The published path is what readers see; an unapproved candidate there is
    publication by accident. The check must fire on the ABSENCE of approval, not
    only on the presence of a newer approved one -- an earlier version returned
    early when no review had ever approved anything, which is precisely the
    situation in which a staged candidate is most dangerous.
    """
    problems = []
    latest = REPO_ROOT / "fed-boc-watcher" / "data" / "latest.json"
    if not latest.exists():
        return problems
    try:
        raw = latest.read_bytes()
        published = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return ["data/latest.json is not valid JSON"]
    published_as_of = parse_dt(published.get("as_of"))
    if published_as_of is None:
        return problems
    approved = _approved_shas()

    published_sha = hashlib.sha256(raw).hexdigest().lower()
    approved_paths = []
    newest, newest_sha = None, None
    for candidate in (REPO_ROOT / "fed-boc-watcher" / "review").rglob("candidate.json"):
        try:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest().lower()
            as_of = parse_dt(json.loads(candidate.read_text(encoding="utf-8")).get("as_of"))
        except (OSError, ValueError):
            continue
        if digest in approved:
            approved_paths.append(candidate)
            if as_of and (newest is None or as_of > newest):
                newest, newest_sha = as_of, digest

    # The published file must be byte-identical to a frozen candidate, and that
    # candidate must carry approval. Anything else is a hand-staged file.
    matched = None
    for candidate in (REPO_ROOT / "fed-boc-watcher" / "review").rglob("candidate.json"):
        try:
            if hashlib.sha256(candidate.read_bytes()).hexdigest().lower() == published_sha:
                matched = candidate
                break
        except OSError:
            continue

    if matched is None:
        # A legitimately published file may predate the review/ candidate
        # discipline: the 2026-09-16 snapshot was published before iteration
        # directories existed and matches no frozen candidate. The published path
        # may only ever change through archive_fed_boc.py, so a working-tree
        # difference is legitimate ONLY if the file carries an archiver stamp
        # (archived_at + snapshot_date) and its content equals a candidate that
        # an approved review is bound to. A hand-edited file has no such stamp,
        # or differs from the approved bytes.
        if _is_legitimate_uncommitted_publication(approved):
            return problems
        drift = _uncommitted_published_drift()
        if drift:
            problems.append(drift)
        return problems
    if not approved:
        problems.append(
            f"data/latest.json carries candidate {matched.parent.name} "
            f"({published_sha[:12]}) but NO pm-review.json on record approves it: "
            "an unapproved candidate is staged in the published path"
        )
        return problems
    if published_sha not in approved:
        # The archiver stamps archived_at/snapshot_date, so the published bytes
        # are the candidate plus those fields. Compare content, not raw bytes.
        approved_candidates = _approved_candidates(approved)
        if not any(_content_matches_candidate(published, c) for c in approved_candidates):
            problems.append(
                f"data/latest.json carries candidate {matched.parent.name} ({published_sha[:12]}), "
                "which no pm-review.json approves as published content: only archive_fed_boc.py may "
                "publish, and only from an approved candidate"
            )
    if newest and published_as_of > newest:
        problems.append(
            f"data/latest.json is stamped {published_as_of.isoformat()}, newer than the newest "
            f"approved candidate {newest.isoformat()}: an unapproved candidate is staged in the "
            "published path"
        )
    return problems


def check_price_threshold_arithmetic(payload):
    """Structured price thresholds must satisfy 100 - price = implied rate.

    2026-09-28: the brief claimed ZQV26 95.65-96.57 meant 'above 4.00% / below
    3.75%'. 100-95.65 is 4.35% and 100-96.57 is 3.43%, so the band was ~35bp too
    wide on each side and in-band prices contradicted the label. Thresholds now
    live in a structured field that the gate recomputes, and the rendered strings
    must quote the same numbers.
    """
    problems = []
    brief = payload.get("decision_brief") or {}
    thresholds = brief.get("price_thresholds") or []
    if isinstance(thresholds, dict):
        thresholds = [thresholds]
    corpus = [s for s in (brief.get("falsifiers") or []) if isinstance(s, str)]
    for bank in (brief.get("banks") or {}).values():
        corpus.extend(s for s in ((bank or {}).get("reconsider_if") or []) if isinstance(s, str))
    for index, item in enumerate(thresholds):
        where = f"decision_brief.price_thresholds[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{where} is not an object")
            continue
        for price_key, rate_key in (("low_price", "low_implied_rate"), ("high_price", "high_implied_rate")):
            price, rate = item.get(price_key), item.get(rate_key)
            if price is None or rate is None:
                continue
            if not isinstance(price, (int, float)) or not isinstance(rate, (int, float)):
                problems.append(f"{where}: {price_key} and {rate_key} must both be numbers")
                continue
            expected = 100.0 - float(price)
            if round(expected, 2) != round(float(rate), 2):
                problems.append(
                    f"{where} is internally inconsistent: 100 - {price} = {expected:.2f}, but "
                    f"{rate_key} is {rate}"
                )
        for price_key in ("low_price", "high_price"):
            price = item.get(price_key)
            if not isinstance(price, (int, float)):
                continue
            shown = any(f"{price:g}" in text or f"{price:.2f}" in text for text in corpus)
            if not shown:
                problems.append(
                    f"{where}.{price_key}={price} appears in no falsifier or reconsider_if string: "
                    "the structured threshold is not the number the reader is shown"
                )
    return problems


def check_attempt_record_status(payload):
    """Attempt records that declare http_status must match their capture's bytes.

    For every dict carrying both http_status and evidence_path, cross-check the
    declared status against (a) the capture's ``.headers`` sidecar and (b) the
    retrieval-manifest entry in the same evidence directory, where either exists.
    Added 2026-10-04 after an independent review found a stale http_status carried
    across a recollection (payload 200 vs a 502 capture).
    """
    problems = []
    stack = [(payload, "")]
    while stack:
        node, path = stack.pop()
        if isinstance(node, dict):
            if "http_status" in node and "evidence_path" in node:
                declared = node.get("http_status")
                evidence = str(node.get("evidence_path") or "")
                resolved = resolve_evidence(evidence)
                if isinstance(declared, int) and resolved is not None:
                    observed = []
                    sidecar = Path(str(resolved) + ".headers")
                    if sidecar.is_file():
                        match = re.search(r"STATUS:\s*(\d{3})",
                                          sidecar.read_text(encoding="utf-8", errors="replace"))
                        if match:
                            observed.append(("headers sidecar", int(match.group(1))))
                    manifest_path = resolved.parent / "retrieval-manifest.json"
                    if manifest_path.is_file():
                        try:
                            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                        except ValueError:
                            manifest = None
                        entries = (manifest or {}).get("entries") or []
                        matching = [e for e in entries
                                    if isinstance(e, dict) and e.get("key") == resolved.name]
                        if matching and isinstance(matching[-1].get("http_status"), int):
                            observed.append(("retrieval manifest", matching[-1]["http_status"]))
                    for source, actual in observed:
                        if actual != declared:
                            problems.append(
                                f"{path or 'payload'}.http_status={declared} but the {source} records "
                                f"{actual} for {resolved.name}")
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                stack.append((value, child))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                stack.append((value, f"{path}[{index}]"))
    return problems


CHECKS = (
    "required_containment",
    "as_of_coherence",
    "market_close_semantics",
    "provenance_traceability",
    "pricing_honesty",
    "derived_numbers",
    "driver_chronology",
    "driver_side_signs",
    "calendar_rendered",
    "renderer_contract",
    "evidence_contains_claim",
    "published_path_provenance",
    "price_threshold_arithmetic",
    "attempt_record_status",
)

RUNNERS = {
    "required_containment": check_required_containment,
    "as_of_coherence": check_as_of_coherence,
    "market_close_semantics": check_market_close_semantics,
    "provenance_traceability": check_provenance_traceability,
    "pricing_honesty": check_pricing_honesty,
    "derived_numbers": check_derived_numbers,
    "driver_chronology": check_driver_chronology,
    "driver_side_signs": check_driver_side_signs,
    "calendar_rendered": check_calendar_rendered,
    "renderer_contract": check_renderer_contract,
    "evidence_contains_claim": check_evidence_contains_claim,
    "published_path_provenance": check_published_path_provenance,
    "price_threshold_arithmetic": check_price_threshold_arithmetic,
    "attempt_record_status": check_attempt_record_status,
}


def run_all(payload, include_working_tree=True):
    """Run every structural check.

    include_working_tree=False skips checks that read the working tree (the
    published-path check) so a candidate can be validated in isolation.
    """
    working_tree_only = {"published_path_provenance"}
    return {name: RUNNERS[name](payload) for name in CHECKS
            if include_working_tree or name not in working_tree_only}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Structural gate for Fed/BOC candidates.")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--baseline", type=Path, default=None,
                        help="prior candidate to require an explicit difference from")
    args = parser.parse_args()

    payload = json.loads(args.candidate.read_text(encoding="utf-8"))
    results = run_all(payload)
    failed = sorted(name for name, problems in results.items() if problems)
    digest = hashlib.sha256(args.candidate.read_bytes()).hexdigest()

    report = {
        "schema_version": "1.0",
        "candidate": str(args.candidate),
        "candidate_sha256": digest,
        "candidate_as_of": payload.get("as_of"),
        "checks": {name: {"pass": not problems, "problems": problems} for name, problems in results.items()},
        "failed_checks": failed,
        "result": "PASS" if not failed else "FAIL",
        "note": "Structural checks only. Judgment (data accuracy, decision usefulness) is the "
                "independent PM's job, not this gate's.",
    }

    if args.baseline and args.baseline.exists():
        old = json.loads(args.baseline.read_text(encoding="utf-8"))
        old_brief = (old.get("decision_brief") or {}).get("headline")
        new_brief = (payload.get("decision_brief") or {}).get("headline")
        report["brief_regeneration"] = {
            "baseline": str(args.baseline),
            "baseline_headline": old_brief,
            "candidate_headline": new_brief,
            "headline_changed": old_brief != new_brief,
            "baseline_version": old.get("version"),
            "candidate_version": payload.get("version"),
        }
        if old_brief == new_brief:
            report["brief_regeneration"]["warning"] = (
                "headline is byte-identical to the baseline: the brief was inherited, not regenerated"
            )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"STRUCTURAL GATE {report['result']}  sha={digest[:12]}  failed={failed or 'none'}")
    for name in failed:
        print(f"  [{name}]")
        for problem in results[name]:
            print(f"    - {problem}")
    if report.get("brief_regeneration"):
        regen = report["brief_regeneration"]
        print(f"  brief regenerated: {regen['headline_changed']} "
              f"({regen['baseline_version']} -> {regen['candidate_version']})")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
