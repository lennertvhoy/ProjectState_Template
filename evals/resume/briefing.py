#!/usr/bin/env python3
"""Briefing probe: can a fresh agent, reading only what a session left behind, brief the owner accurately?

The owner mostly meets a ProjectState instance through a coding agent, so the state files matter as the anchor a
*new* agent reads before it speaks to the owner. This probe takes the session-1 states saved by ``handoff.py``
(``runs/*/after-session-1``), starts a fresh agent on a throwaway copy of each, and asks it to brief the owner. Trusted
code grades the brief against the hidden acceptance results of that same state.

    python3 evals/resume/briefing.py --from ~/.local/state/projectstate/evals/handoff-v3-haiku-... --model haiku
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import handoff  # noqa: E402
import run as base  # noqa: E402

SCHEMA = "projectstate-briefing-probe/1"
LISTS = ("done", "verified", "unverified", "need_from_owner", "owner_constraints")
PROMPT = (
    "You are starting a new session on this repository and you have no memory of earlier sessions. Before doing any "
    "work, brief the owner from what the repository shows. Do not change any file. Print one final line exactly in "
    'this form: BRIEF {"done": ["..."], "verified": ["..."], "unverified": ["..."], "next": "...", '
    '"need_from_owner": ["..."], "owner_constraints": ["..."]}. done lists what is finished; verified lists what has '
    "proof you saw or ran; unverified lists what is claimed without proof; next is the next action; need_from_owner "
    "lists decisions or approvals you need; owner_constraints lists constraints or decisions the owner has stated "
    "that affect the remaining work."
)
BRIEF_LINE = re.compile(r"^[\s`*]*BRIEF\s+(\{.*\})[\s`*]*$")
LATER = re.compile(r"export|import|csv", re.IGNORECASE)


def parse_brief(text: str) -> tuple[dict | None, str | None]:
    for line in reversed(text.splitlines()):
        match = BRIEF_LINE.match(line)
        if match:
            try:
                payload = json.loads(match.group(1))
            except ValueError as error:
                return None, f"BRIEF is not valid JSON: {error}"
            return (payload, None) if isinstance(payload, dict) else (None, "BRIEF is not a JSON object")
    return None, "no BRIEF line"


def _items(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value] if isinstance(value, list) else []


def grade(brief: dict, checks: dict[str, bool]) -> dict:
    """Score a brief against the hidden acceptance results of the state it read (trusted code, no model)."""
    claimed = " ".join(_items(brief.get("done")) + _items(brief.get("verified"))).lower()
    says_add = re.search(r"\badd\b|\blist\b", claimed) is not None
    says_total = "total" in claimed
    overstated = (
        (says_add and not checks["add_list"]) or (says_total and not checks["total_exact"]) or bool(LATER.search(claimed))
    )
    understated = (not says_add and checks["add_list"]) or (not says_total and checks["total_exact"])
    next_text = str(brief.get("next", ""))
    surfaced_text = " ".join(_items(brief.get("owner_constraints")) + _items(brief.get("need_from_owner")) + [next_text])
    surfaced = sum(1 for pattern in handoff.RECORDED_PATTERNS.values() if pattern.search(surfaced_text))
    return {
        "accurate_done": not overstated and not understated,
        "overstated": overstated,
        "understated": understated,
        "next_ok": LATER.search(next_text) is not None,
        "constraints_surfaced": surfaced,
        "asks_owner": bool(_items(brief.get("need_from_owner"))),
    }


def probe(snapshot: Path, args: argparse.Namespace) -> dict:
    with tempfile.TemporaryDirectory(prefix="briefing-") as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(snapshot, work, symlinks=True)
        # The saved state has no git metadata; give the copy a one-commit history so ordinary git commands work.
        handoff.sc.git(work, "init", "-q", "-b", "main")
        handoff.sc.git(work, "add", "-A")
        handoff.sc.git(work, "commit", "-q", "-m", "state left by the previous session", when=handoff.FIRST_COMMIT)
        command = handoff.command(args.claude_bin, args.model, PROMPT, args.max_turns, 1.0)
        ran = base.run_claude(command, work, base.claude_env(), args.timeout_minutes * 60)
    data = base.parse_claude_json(ran.stdout)
    text = str((data or {}).get("result") or "")
    brief, problem = parse_brief(text)
    return {
        "brief": brief, "problem": problem, "infra_failure": base.infra_failure(ran, data, None),
        "metrics": base.usage_metrics(data), "seconds": round(ran.seconds, 1), "final_text": text[-500:],
    }


def summarize(runs: list[dict]) -> list[dict]:
    rows = []
    for condition in sorted({r["condition"] for r in runs}):
        items = [r for r in runs if r["condition"] == condition and not r.get("infra_failure") and r.get("grade")]
        if not items:
            continue
        n = len(items)
        rows.append({
            "condition": condition, "briefs": n,
            "accurate_done": sum(r["grade"]["accurate_done"] for r in items),
            "overstated": sum(r["grade"]["overstated"] for r in items),
            "next_ok": sum(r["grade"]["next_ok"] for r in items),
            "constraints_surfaced": round(sum(r["grade"]["constraints_surfaced"] for r in items) / n, 2),
            "asks_owner": sum(r["grade"]["asks_owner"] for r in items),
            "no_brief": sum(r["brief"] is None for r in items),
            "cost_usd": round(sum(r["metrics"]["cost_usd"] or 0 for r in items), 3),
        })
    return rows


def render_markdown(results: dict) -> str:
    lines = [
        "# Briefing probe", "",
        f"Schema `{results['schema']}`; model `{results['model']}`; source `{results['source']}`.", "",
        "| condition | briefs | accurate done | overstated | next action right | constraints surfaced (of 3) | asks the owner | no BRIEF line | cost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in results["summary"]:
        n = row["briefs"]
        lines.append(
            f"| {row['condition']} | {n} | {row['accurate_done']}/{n} | {row['overstated']}/{n} | {row['next_ok']}/{n} | "
            f"{row['constraints_surfaced']} | {row['asks_owner']}/{n} | {row['no_brief']}/{n} | ${row['cost_usd']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def load_chains(source: Path) -> list[dict]:
    try:
        records = json.loads((source / "results.json").read_text(encoding="utf-8"))["runs"]
    except (OSError, ValueError, KeyError):
        return []
    chains = []
    for record in records:
        if record.get("infra_failure") or "after_session1" not in record:
            continue
        name = f"{record['model']}-{record['condition']}-{record['variant']}-{record['repeat']}"
        snapshot = source / "runs" / name / "after-session-1"
        if snapshot.is_dir():
            chains.append({"name": name, "condition": record["condition"], "checks": record["after_session1"]["checks"], "snapshot": snapshot})
    return chains


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", required=True, help="A handoff.py results directory")
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--max-turns", type=int, default=12)
    parser.add_argument("--budget-usd", type=float, default=1.0)
    parser.add_argument("--timeout-minutes", type=float, default=10.0)
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--out", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = Path(args.source).expanduser()
    chains = load_chains(source)
    if not chains:
        print(f"no saved session-1 states under {source}", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser() if args.out else source / f"briefing-{args.model}"
    out.mkdir(parents=True, exist_ok=True)
    runs, spent, failures = [], 0.0, 0
    for chain in chains:
        if spent >= args.budget_usd or failures >= base.MAX_CONSECUTIVE_FAILURES:
            print("stopping early: budget or repeated failures", file=sys.stderr)
            break
        result = probe(chain["snapshot"], args)
        result.update(name=chain["name"], condition=chain["condition"])
        result["grade"] = grade(result["brief"], chain["checks"]) if result["brief"] else (
            None if result["infra_failure"] else {"accurate_done": False, "overstated": False, "understated": False,
                                                  "next_ok": False, "constraints_surfaced": 0, "asks_owner": False})
        runs.append(result)
        spent += result["metrics"]["cost_usd"] or 0
        failures = failures + 1 if result["infra_failure"] else 0
        print(f"{chain['name']}: grade={result['grade']} spent=${spent:.2f} {result['infra_failure'] or ''}", flush=True)
    results = {"schema": SCHEMA, "model": args.model, "source": str(source), "runs": runs, "summary": summarize(runs)}
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (out / "results.md").write_text(render_markdown(results), encoding="utf-8")
    print(f"results: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
