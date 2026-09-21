"""Equal-weight map scores, explicit missing coverage, and paired regressions."""
import json
from pathlib import Path

POINTS = {'loss': 0, 'draw': 0.5, 'win': 1}


def scorecard(before, after, maps, opponents):
    rows = []
    for name in maps:
        expected = {(enemy, name, side) for enemy in opponents for side in 'AB'}
        complete = all(k in before and k in after and before[k] in POINTS and
                       after[k] in POINTS for k in expected)
        row = dict(map=name, complete=complete, expected_pairs=len(expected),
                   completed_pairs=sum(k in before and k in after for k in expected))
        row['before'] = 100*sum(POINTS[before[k]] for k in expected)/len(expected) if complete else None
        row['after'] = 100*sum(POINTS[after[k]] for k in expected)/len(expected) if complete else None
        row['regressions'] = [dict(opponent=k[0], side=k[2]) for k in sorted(expected)
                              if k in before and k in after and
                              before[k] in POINTS and after[k] in POINTS and
                              POINTS[after[k]] < POINTS[before[k]]]
        rows.append(row)
    complete = bool(rows) and all(r['complete'] for r in rows)
    return dict(maps=rows, complete=complete,
                macro_before=sum(r['before'] for r in rows)/len(rows) if complete else None,
                macro_after=sum(r['after'] for r in rows)/len(rows) if complete else None,
                priority=[r['map'] for r in sorted(rows, key=lambda r:
                          (not bool(r['regressions']), r['after'] if r['after'] is not None else -1))])


def write_scorecard(out, before, after, maps, opponents):
    data = scorecard(before, after, maps, opponents)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out/'map_scores.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    lines = ['# Scores by map', '',
             'Each map has equal weight. WIN=1, DRAW=0.5, LOSS=0. Missing games do not count as wins or losses; the overall score is withheld until coverage is complete.', '',
             '| Map | Paired coverage | Before /100 | After /100 | Regressions |',
             '|---|---:|---:|---:|---|']
    for row in data['maps']:
        fmt = lambda value: 'missing' if value is None else f'{value:.1f}'
        lines.append(f"| {row['map']} | {row['completed_pairs']}/{row['expected_pairs']} | {fmt(row['before'])} | {fmt(row['after'])} | {row['regressions']} |")
    lines += ['', f"All-map mean: {data['macro_before']} -> {data['macro_after']}", '',
              'Investigate in order: '+', '.join(data['priority']), '',
              'Scores locate weaknesses; replay inspection is required before assigning a cause. Improvements cannot compensate for regressions in another map or starting side.']
    (out/'map_scores.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return data
