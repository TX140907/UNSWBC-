"""Measure replay behavior, preserving match and submission identities.

Run: python battlecode_data/study_strategies.py
No downloads or changes to bot code. Uses the local validated replay reader.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from analyze_replays import analyze
from make_dataset import Board
from replay_reader import load_replay

ROOT = Path(__file__).resolve().parent


def study(path):
    summary = analyze(path)  # also checks final reconstruction against replay result
    replay = load_replay(path)
    board = Board(replay['map'])
    meta_path = path.with_suffix('.meta.json')
    meta = json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if meta.get('sha256') and meta['sha256'] != sha:
        raise ValueError(f'Checksum mismatch: {path}')
    summary['sha256'] = sha
    summary['path'] = str(path.relative_to(ROOT.parent))
    births, death_rounds = {}, {}
    for team, row in summary['teams'].items():
        row['submission_id'] = meta.get(f'submission{team}Id')
        row['split_shapes'] = Counter()
        row['split_phases'] = Counter()
        row['split_unit_counts'] = Counter()
        row['sprint_lengths'] = Counter()
        row['turns_with_sprint_death'] = 0
        row['turns_with_move_death'] = 0
        row['turns_changing_direction'] = 0
        row['rescue_shape_examples'] = []
        row['sprint_examples'] = []
    pending = {}
    for event in replay['events']:
        kind = event['type']
        if kind == 'turnStart':
            pending = {}
        elif kind == 'dragonAction':
            dragon = board.dragons[event['id']]
            row = summary['teams'][dragon['team']]
            action = event['action']
            if action['kind'] == 'move':
                steps = action['steps']
                row['turns_changing_direction'] += bool(steps and steps[0] != dragon['facing'])
                pending = {'id': event['id'], 'sprint': len(steps) > 1}
                if len(steps) > 1:
                    row['sprint_lengths'][str(len(steps))] += 1
                    if len(row['sprint_examples']) < 5:
                        row['sprint_examples'].append(dict(round=board.round, id=event['id'],
                            length=len(dragon['body']), steps=steps, head=dragon['body'][0]))
        elif kind == 'dragonSplit':
            row = summary['teams'][event['team']]
            parent, child = len(event['parent_body']), len(event['child_body'])
            before = len(board.dragons[event['parent_id']]['body'])
            assert parent + child == before
            row['split_shapes'][f'{before}->{parent}+{child}'] += 1
            phase = '0-99' if board.round < 100 else '100-349' if board.round < 350 else '350-499'
            row['split_phases'][phase] += 1
            units = sum(d['team'] == event['team'] for d in board.dragons.values())
            row['split_unit_counts'][str(units)] += 1
            births[event['child_id']] = (event['team'], board.round)
            if parent == 2 and child > 2 and len(row['rescue_shape_examples']) < 5:
                row['rescue_shape_examples'].append(dict(round=board.round, parent_id=event['parent_id'],
                    child_id=event['child_id'], before=before, parent=parent, child=child))
        elif kind == 'dragonDeath':
            death_rounds[event['id']] = board.round
            if pending.get('id') == event['id']:
                row = summary['teams'][board.dragons[event['id']]['team']]
                key = 'turns_with_sprint_death' if pending['sprint'] else 'turns_with_move_death'
                row[key] += 1
        board.apply(event)
    for team, row in summary['teams'].items():
        children = [(i, born) for i, (t, born) in births.items() if t == team]
        eligible = [(i, born) for i, born in children if born + 10 <= board.round]
        row['child_10_rounds'] = dict(eligible=len(eligible),
            survived=sum(death_rounds.get(i, board.round + 1) >= born + 10 for i, born in eligible))
        row['checkpoints'] = [t for t in summary['timeline'] if t['team'] == team and
                              t['round'] in (49, 99, 199, 349, 449, 499)]
    return summary


def main():
    out = ROOT / 'strategy_study'
    out.mkdir(exist_ok=True)
    matches, seen = [], set()
    for directory in ('top_replays', 'replays', 'all_replays'):
        for path in sorted((ROOT / directory).glob('*.replay')):
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if sha in seen:
                continue
            seen.add(sha)
            row = study(path)
            if row['result']['terminated']:
                matches.append(row)
            print(f'Checked {path.name}: {row["map_name"]}', flush=True)
    (out / 'measurements.json').write_text(json.dumps(matches, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Replay strategy measurements', '',
             f'{len(matches)} unique completed matches; '
             f'{len({m["group_id"] for m in matches})} series/groups. All final standings reconstructed and checked.', '',
             'Counts describe observed actions, not hidden intent or causal effects. '
             'Parent=2 is a split shape, not proof of a rescue. Round numbers start at zero. '
             '10-round survival excludes children born in the final ten rounds. '
             'Same-turn deaths omit deaths later in the round; sprint/move risks are not directly comparable.', '',
             '| Match / map | Side / team / submission | W/L | Splits early / middle / late | Frequent split shapes (before -> parent + child) | Peak units | Final units / longest | Child survival 10 rounds | Sprint / moves |',
             '|---|---|---|---|---|---:|---|---|---|']
    for m in matches:
        for side, r in m['teams'].items():
            outcome = 'D' if m['result']['winner'] is None else 'W' if m['result']['winner'] == side else 'L'
            phases = ' / '.join(str(r['split_phases'].get(p, 0)) for p in ('0-99','100-349','350-499'))
            shapes = ', '.join(f'{k}: {v}' for k,v in r['split_shapes'].most_common(3))
            life = r['child_10_rounds']; final = r['final']
            lines.append(f'| {m["match_id"] or m["file"]} / {m["map_name"]} | '
                         f'{side} / {r["name"]} / {r["submission_id"]} | {outcome} | {phases} | {shapes} | '
                         f'{r["peak_units"]} | {final["dragon_count"]} / {final["longest_dragon"]} | '
                         f'{life["survived"]}/{life["eligible"]} | {r["sprint_actions"]}/{r["move_actions"]} |')
    (out / 'measurements.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Wrote {out}', flush=True)


if __name__ == '__main__':
    main()
