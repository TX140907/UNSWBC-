"""Optional four-direction imitation baseline. Requires scikit-learn.

This trains a decision tree to imitate observed single-step moves. It does not
train Codex, implement RL, or produce a complete tournament bot.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import random


def features(obs):
    # Explicit input whitelist: no winner, death label, bot name, match ID,
    # map text, future events, hidden tiles, or other dragons' hidden bodies.
    values = [obs['length'], obs['unit_count'], obs['round'], *obs['map']]
    values.extend(int(obs['facing'] == d) for d in 'NESW')
    for tile in obs['tiles']:
        pearl, timer, occupant = tile[:3]
        # Portal IDs are omitted; only the visible edge type is a feature.
        values.extend([pearl, timer, occupant, tile[3], tile[5], tile[7], tile[9]])
    return values


def train(path, output, max_per_split=100000):
    import numpy as np
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix

    data = {s: [] for s in ('train', 'validation', 'test')}
    seen = Counter()
    group_splits = {}
    rng = random.Random(42)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            sample = json.loads(line)
            split, group = sample['split'], sample['group_id']
            if group in group_splits and group_splits[group] != split:
                raise ValueError('Same match/series appears in more than one split')
            group_splits[group] = split
            a = sample['action']
            if not sample['team_won'] or sample['died_this_turn'] or a['kind'] != 'move' or len(a['steps']) != 1:
                continue
            if a['steps'] not in 'NESW':
                raise ValueError('Unknown direction label')
            item = (features(sample['observation']), 'NESW'.index(a['steps']), group)
            seen[split] += 1
            if len(data[split]) < max_per_split:
                data[split].append(item)
            else:
                index = rng.randrange(seen[split])
                if index < max_per_split:
                    data[split][index] = item
    if any(not data[s] for s in data):
        raise ValueError('Need usable examples in train, validation AND test. Download more independent matches; do not randomly split individual turns.')
    def arrays(rows):
        return np.asarray([r[0] for r in rows], dtype=np.float32), np.asarray([r[1] for r in rows])
    x, y = arrays(data['train'])
    model = DecisionTreeClassifier(max_depth=10, min_samples_leaf=20, random_state=42)
    model.fit(x, y)
    reports = {}
    for split in data:
        sx, sy = arrays(data[split])
        prediction = model.predict(sx)
        reports[split] = {'samples': len(sy), 'groups': len({r[2] for r in data[split]}),
                          'accuracy': float(accuracy_score(sy, prediction)),
                          'balanced_accuracy': float(balanced_accuracy_score(sy, prediction)),
                          'confusion_matrix_NESW': confusion_matrix(sy, prediction, labels=[0,1,2,3]).tolist()}
    tree = model.tree_
    payload = {'description': 'Single-step imitation policy; requires legal-action safety wrapper and game evaluation',
               'directions': 'NESW', 'feature_count': len(x[0]), 'feature_version': 1,
               'children_left': tree.children_left.tolist(), 'children_right': tree.children_right.tolist(),
               'feature': tree.feature.tolist(), 'threshold': tree.threshold.tolist(),
               'classes': model.classes_.tolist(), 'value': tree.value[:, 0, :].tolist(),
               'metrics': reports}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(reports, indent=2))
    print(f'Saved policy: {output}')
    print('Accuracy measures imitation, not game win rate. Evaluate in the engine before using this policy.')
    return payload


def predict(policy, observation):
    """Pure-Python inference for the exported JSON; returns directions by score.

    A bot must reject unsafe/illegal moves separately. This model cannot split,
    sprint, plan with portal memory or coordinate using sonar.
    """
    x = features(observation)
    node = 0
    while policy['children_left'][node] != -1:
        node = (policy['children_left'][node] if x[policy['feature'][node]] <= policy['threshold'][node]
                else policy['children_right'][node])
    scores = dict(zip(policy['classes'], policy['value'][node]))
    return sorted('NESW', key=lambda d: scores.get('NESW'.index(d), 0), reverse=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset', type=Path)
    p.add_argument('--output', type=Path, default=Path('move_policy.json'))
    p.add_argument('--max-per-split', type=int, default=100000)
    args = p.parse_args()
    if args.max_per_split <= 0:
        p.error('--max-per-split must be positive')
    try:
        train(args.dataset, args.output, args.max_per_split)
    except (ValueError, ImportError) as error:
        p.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
