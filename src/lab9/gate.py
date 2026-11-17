"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)
    Also checked: duplicated (item, seed) rows, and metric values that do not follow from the rows
    (a hand-edited report)."""
    problems: list[str] = []
    rows = pr.get("rows") or []
    man = pr.get("manifest") or {}

    # 1. metric values that cannot be compared with a threshold
    for k, v in (pr.get("metrics") or {}).items():
        if isinstance(v, float) and not math.isfinite(v):
            problems.append(f"metric {k} is {v}: NaN/inf compares False against every threshold")

    # 2. dropped or duplicated rows
    want_rows = int(man.get("items", 0)) * len(man.get("seeds") or [])
    if len(rows) != want_rows:
        problems.append(f"{len(rows)} rows, manifest promises {man.get('items')} items x "
                        f"{len(man.get('seeds') or [])} seeds = {want_rows}")
    keys = [(r["item_id"], r["seed"]) for r in rows]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        problems.append(f"duplicated (item, seed) rows, first: {dup[0]}")

    # 3. a different (item, seed) set than the baseline's (cherry-picked seeds or items)
    base_keys = [(r["item_id"], r["seed"]) for r in base.get("rows") or []]
    only_pr, only_base = set(keys) - set(base_keys), set(base_keys) - set(keys)
    if only_pr or only_base:
        problems.append(f"(item, seed) set differs from the baseline: {len(only_base)} missing, {len(only_pr)} extra")

    # 4. broken graders: reported failures, or a graded metric whose row value is not a plain bool
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s), first: {pr['evaluator_failures'][0]}")
    graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
    bad_rows = [(r["item_id"], r["seed"], m) for r in rows for m in graded if not isinstance(r.get(m), bool)]
    if bad_rows:
        problems.append(f"{len(bad_rows)} row value(s) are None/missing/not bool for a graded metric, "
                        f"first: {bad_rows[0]} (a crashed grader drops out of the mean)")

    # 5. reported metrics must follow from the rows (no hand-editing)
    for m in graded:
        vals = [r[m] for r in rows if isinstance(r.get(m), bool)]
        if m not in (pr.get("metrics") or {}) or not vals:
            continue
        got = sum(vals) if m in ("secret_leak", "approval_bypass") else sum(vals) / len(vals)
        rep = pr["metrics"][m]
        if isinstance(rep, (int, float)) and math.isfinite(rep) and abs(rep - got) > 1e-3:
            problems.append(f"metric {m} reports {rep} but the rows give {got:.4f}")

    # 6. item slice tags changed relative to the baseline
    # per (item, seed) row, not per item: relabelling some rows of an item must not be hidden by the others
    tags = lambda rep: {(r["item_id"], r["seed"]): sorted(r.get("slices") or []) for r in rep.get("rows") or []}
    tp, tb = tags(pr), tags(base)
    moved = sorted(k for k in tp.keys() & tb.keys() if tp[k] != tb[k])
    if moved:
        problems.append(f"slice tags differ from the baseline for {len(moved)} row(s), first: {moved[0]}")

    # 7. ratchet: on the same eval-set version, nothing may get looser than the base spec
    if base_spec is not None and base_spec.get("eval_set_version") == spec.get("eval_set_version"):
        problems += _ratchet(spec, base_spec)
    return problems


def _looser(new: dict, old: dict, where: str) -> list[str]:
    """Threshold fields of one metric or slice: what may never get weaker."""
    out = []
    n_th, o_th = new.get("threshold", new), old.get("threshold", old)
    if "min" in o_th and ("min" not in n_th or n_th["min"] < o_th["min"]):
        out.append(f"{where}: min fell from {o_th['min']} to {n_th.get('min')}")
    for key in ("max", "max_increase"):
        if key in o_th and (key not in n_th or n_th[key] > o_th[key]):
            out.append(f"{where}: {key} rose from {o_th[key]} to {n_th.get(key)}")
    if o_th.get("no_significant_drop") and not n_th.get("no_significant_drop"):
        out.append(f"{where}: no_significant_drop was dropped")
    if old.get("blocking") and not new.get("blocking"):
        out.append(f"{where}: no longer blocking")
    return out


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    problems: list[str] = []
    new_m = {m["id"]: m for m in spec.get("metrics") or []}
    for old in base_spec.get("metrics") or []:
        new = new_m.get(old["id"])
        if new is None:
            problems.append(f"metric {old['id']} disappeared from the spec")
            continue
        if new.get("grader") != old.get("grader"):
            problems.append(f"metric {old['id']}: grader changed from {old.get('grader')!r} to {new.get('grader')!r}")
        problems += _looser(new, old, f"metric {old['id']}")
    new_s = {(s["name"], s["metric"]): s for s in spec.get("slices") or []}
    for old in base_spec.get("slices") or []:
        new = new_s.get((old["name"], old["metric"]))
        if new is None:
            problems.append(f"slice {old['name']}/{old['metric']} disappeared from the spec")
            continue
        problems += _looser(new, old, f"slice {old['name']}/{old['metric']}")
    if not set(base_spec.get("seeds") or []) <= set(spec.get("seeds") or []):
        problems.append(f"seeds shrank from {base_spec.get('seeds')} to {spec.get('seeds')}")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        sid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        verdict, note = "ok", ""
        if not a:
            # A slice with no scored items cannot be passed: dropping the items or relabelling
            # them out of the slice must not hide a regression.
            verdict, value = "missing", None
        else:
            value = sum(a.values()) / len(a)
            if "min" in sl and value < sl["min"]:
                verdict = "fail"
            if sl.get("no_significant_drop"):
                keys = sorted(set(a) & set(b))
                if len(keys) >= 2:
                    d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                       n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
                    note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    if hi < 0:
                        verdict = "fail"
                elif verdict == "ok":
                    verdict = "missing"       # too few shared items to test for a drop
        if verdict != "ok" and sl.get("blocking"):
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if sl.get("blocking") else "warn")
        shown = "-" if value is None else f"{value:.4f}"
        lines.append(f"  {sid:<34} {shown:<8} {json.dumps({k: sl[k] for k in ('min',) if k in sl}):<14} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
