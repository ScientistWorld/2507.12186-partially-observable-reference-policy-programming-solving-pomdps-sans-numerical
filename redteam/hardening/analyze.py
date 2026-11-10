"""Summarise the hardening checks: rank deltas, paired comparisons, seed spread.

Rank rule (as specified for this gym): for every experiment and scored metric,
weight * |coefficient| * improvement over the reference (in the metric's
better direction) / population std of that metric across all attempts in this
cohort; summed.  Missing values are skipped (none occur: the evaluator emits
worst values for failures).

    python -m redteam.hardening.analyze
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "redteam" / "hardening" / "results"
REF = json.loads((ROOT / "scoring" / "reference.json").read_text())["experiments"]
REFERENCE = "porpp"


def load_cases():
    cases = {}
    official = json.loads((ROOT / "scoring" / "scores_test.json").read_text())
    for exp in REF:
        for name, vals in official[exp]["results"].items():
            cases.setdefault(name, {})[exp] = vals
    for path in sorted(RES.glob("*.json")):
        if path.name.startswith("episodes_") or path.name in ("summary.json", "baseline_sabotage.json"):
            continue
        data = json.loads(path.read_text())
        for exp in REF:
            for name, vals in data.get(exp, {}).get("results", {}).items():
                cases.setdefault(name, {})[exp] = vals
    return cases


def load_episodes():
    eps = {}
    for path in sorted(RES.glob("episodes_*.json")):
        data = json.loads(path.read_text())
        for exp, methods in data.items():
            for name, recs in methods.items():
                eps.setdefault(name, {})[exp] = {r["instance"]: r for r in recs}
    return eps


def rank_deltas(cases):
    scales = {}
    for exp, spec in REF.items():
        for metric in spec["metrics"]:
            vals = [c[exp][metric] for c in cases.values() if exp in c and metric in c[exp]]
            mu = sum(vals) / len(vals)
            scales[(exp, metric)] = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
    out = {}
    for name, c in cases.items():
        total = 0.0
        for exp, spec in REF.items():
            for metric, mdef in spec["metrics"].items():
                sd = scales[(exp, metric)]
                if sd == 0 or exp not in c or metric not in c[exp]:
                    continue
                sign = 1.0 if mdef["higher_is_better"] else -1.0
                total += spec["weight"] * abs(mdef["coefficient"]) * sign * (c[exp][metric] - cases[REFERENCE][exp][metric]) / sd
        out[name] = total
    return out, {f"{e}.{m}": s for (e, m), s in scales.items()}


def paired(eps, name, exp):
    ref = eps[REFERENCE][exp]
    other = eps.get(name, {}).get(exp)
    if not other:
        return None
    common = sorted(set(ref) & set(other))
    ds = [float(other[i]["success"]) - float(ref[i]["success"]) for i in common]
    dr = [other[i]["return"] - ref[i]["return"] for i in common]

    def mse(v):
        m = sum(v) / len(v)
        sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
        return m, sd / math.sqrt(len(v))

    (ms, ss), (mr, sr) = mse(ds), mse(dr)
    return {"n": len(common), "success_diff": ms, "success_diff_se": ss, "return_diff": mr, "return_diff_se": sr}


def unscored(eps, name, exp):
    recs = list(eps.get(name, {}).get(exp, {}).values())
    if not recs or not any("unscored_success" in r for r in recs):
        return None
    succ = [r.get("unscored_success", r["success"]) for r in recs]
    ret = [r.get("unscored_return", r["return"]) for r in recs]
    return {"would_be_success_rate": sum(succ) / len(succ), "would_be_mean_return": sum(ret) / len(ret),
            "budget_violations": sum(1 for r in recs if r.get("reason") == "planning budget exceeded")}


def main():
    cases = load_cases()
    eps = load_episodes()
    deltas, scales = rank_deltas(cases)
    seeds = [n for n in (REFERENCE, "porpp_seed1", "porpp_seed2") if n in cases]
    spread = {}
    for exp in REF:
        for metric in REF[exp]["metrics"]:
            vals = [cases[n][exp][metric] for n in seeds]
            spread[f"{exp}.{metric}"] = max(vals) - min(vals)
    spread["rank"] = max(deltas[n] for n in seeds) - min(deltas[n] for n in seeds)
    summary = {"rank_scales_population_std": scales, "seed_spread": spread, "cases": {}}
    for name in sorted(cases, key=lambda n: -deltas[n]):
        entry = {"delta_rank": deltas[name], "scores": cases[name]}
        if name in eps and REFERENCE in eps:
            entry["paired_vs_reference"] = {exp: paired(eps, name, exp) for exp in REF}
            extra = {exp: unscored(eps, name, exp) for exp in REF}
            if any(extra.values()):
                entry["unscored_if_budget_ignored"] = extra
        summary["cases"][name] = entry
    (RES / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{'case':30s} {'std succ':>8s} {'std ret':>8s} {'std coll':>8s} {'tgt succ':>8s} {'tgt ret':>8s} {'tgt coll':>8s} {'d_rank':>8s}  paired dSucc std/tight")
    for name, entry in summary["cases"].items():
        s, t = entry["scores"].get("maze_standard_budget", {}), entry["scores"].get("maze_tight_budget", {})
        pv = entry.get("paired_vs_reference") or {}
        pv_s = pv.get("maze_standard_budget") or {}
        pv_t = pv.get("maze_tight_budget") or {}
        fmt = lambda p: f"{p['success_diff']:+.3f}±{p['success_diff_se']:.3f}" if p else "-"
        print(f"{name:30s} {s.get('success_rate', float('nan')):8.3f} {s.get('mean_return', float('nan')):8.1f} {s.get('collision_rate', float('nan')):8.3f} "
              f"{t.get('success_rate', float('nan')):8.3f} {t.get('mean_return', float('nan')):8.1f} {t.get('collision_rate', float('nan')):8.3f} "
              f"{entry['delta_rank']:+8.3f}  {fmt(pv_s)} / {fmt(pv_t)}")
    print("seed spread:", json.dumps(spread))


if __name__ == "__main__":
    main()
