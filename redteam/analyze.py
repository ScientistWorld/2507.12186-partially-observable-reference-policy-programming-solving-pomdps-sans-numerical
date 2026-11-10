"""Analyze measured hidden-test scores; not used by any candidate method.

Rank units depend on future attempts. We therefore save raw metric vectors,
dominance comparisons, and two explicitly specified cohort normalizations.
Both use magnitudes of coefficients and higher_is_better, including the
negative coefficient attached to lower-is-better standard error.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pstdev

HERE = Path('/home/user/redteam')
EXP = 'scaled_maze_online_planning'


def read_json(path):
    return json.loads(path.read_text())


def main():
    reference_scores = read_json(HERE / 'original/scoring/scores_test.json')
    specification = read_json(HERE / 'original/scoring/reference.json')['experiments']
    measurements = {}
    for path in sorted(HERE.glob('*/scores_test.json')):
        name = path.parent.name
        status_path = path.parent / 'status.json'
        if status_path.exists() and read_json(status_path).get('status') == 'complete':
            measurements[name] = read_json(path)

    honest_names = [name for name in measurements if not name.startswith('shortcut_')]

    def calibration(names):
        out = {}
        for exp, spec in specification.items():
            out[exp] = {}
            for metric, config in spec['metrics'].items():
                values = []
                for name in names:
                    row = measurements[name].get(exp, {}).get('results', {}).get('porpp', {})
                    if isinstance(row.get(metric), (int, float)):
                        values.append(row[metric])
                out[exp][metric] = pstdev(values) if len(values)>1 else 0.0
        return out

    cohort_scale = calibration(list(measurements))
    honest_scale = calibration(honest_names)

    def rank(scores, scales, key='porpp'):
        result, contributions = 0.0, {}
        for exp, spec in specification.items():
            row = scores.get(exp, {}).get('results', {}).get(key, {})
            ref = reference_scores.get(exp, {}).get('results', {}).get('porpp', {})
            for metric, config in spec['metrics'].items():
                if metric not in row or metric not in ref:
                    continue
                scale = scales[exp][metric]
                if not scale:
                    continue
                sign = 1.0 if config['higher_is_better'] else -1.0
                delta = spec['weight'] * abs(config['coefficient']) * sign * (row[metric]-ref[metric])/scale
                result += delta
                contributions[f'{exp}.{metric}'] = delta
        return result, contributions

    reference_row = reference_scores[EXP]['results']['porpp']
    cases = {}
    for name, scores in measurements.items():
        row = scores.get(EXP, {}).get('results', {}).get('porpp', {})
        shared = [metric for metric, config in specification[EXP]['metrics'].items()
                  if config['coefficient'] and metric in row and metric in reference_row]
        deltas = {metric: (row[metric]-reference_row[metric]) *
                  (1 if specification[EXP]['metrics'][metric]['higher_is_better'] else -1)
                  for metric in shared}
        rank_all, terms_all = rank(scores, cohort_scale)
        rank_honest, terms_honest = rank(scores, honest_scale)
        cases[name] = dict(metrics=row, rank_audit_cohort=rank_all,
                           rank_honest_calibration=rank_honest,
                           contributions_audit_cohort=terms_all,
                           contributions_honest_calibration=terms_honest,
                           pareto_dominates_reference=bool(deltas) and all(v>=-1e-12 for v in deltas.values()) and any(v>1e-12 for v in deltas.values()),
                           scored_methods=sorted(scores.get(EXP,{}).get('results',{})))
        (HERE / name / 'rank.json').write_text(json.dumps(cases[name], indent=2) + '\n')

    seed_names = ['reference_seed7','reference_seed1007','reference_seed2007']
    seed_spread = {}
    if all(name in cases for name in seed_names):
        for metric in specification[EXP]['metrics']:
            values = [cases[name]['metrics'][metric] for name in seed_names]
            seed_spread[metric] = dict(values=values, min=min(values), max=max(values), spread=max(values)-min(values))
        for key in ['rank_audit_cohort', 'rank_honest_calibration']:
            values = [cases[name][key] for name in seed_names]
            seed_spread[key] = dict(values=values, min=min(values), max=max(values), spread=max(values)-min(values))

    # Public split is reconstructed from visible train code, then checked
    # against measured test membership without importing hidden code.
    from eval.train.evaluate_maze import split_bit
    seed_membership = {str(seed): 'test' if split_bit({'seed':seed}) else 'train' for seed in range(7,39)}
    output = dict(reference=reference_row, seed_spread=seed_spread,
                  rank_definition='sum(weight * abs(coefficient) * direction * (attempt-reference)/population_std); missing values skipped; zero-variance metrics contribute zero',
                  audit_cohort=list(measurements), honest_calibration=honest_names,
                  audit_cohort_std=cohort_scale, honest_calibration_std=honest_scale,
                  public_seed_membership=seed_membership, cases=cases)
    (HERE / 'summary.json').write_text(json.dumps(output, indent=2) + '\n')
    lines = ['| Case | Success | Reward | Claim margin | Claim | Episodes | Rank (audit cohort) |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for name, case in cases.items():
        row = case['metrics']
        if row:
            lines.append(f"| {name} | {row['success_rate']:.6f} | {row['mean_total_reward']:.6g} | {row['core_claim_margin_score']:.6f} | {row['core_claim_supported']:.0f} | {row['episodes']} | {case['rank_audit_cohort']:+.6f} |")
        else:
            lines.append(f"| {name} | missing | missing | missing | missing | missing | {case['rank_audit_cohort']:+.6f} |")
    (HERE / 'results.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
    print('Seed spread:', json.dumps(seed_spread))


if __name__ == '__main__':
    main()
