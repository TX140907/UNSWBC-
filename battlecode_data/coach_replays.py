"""Local replay audit + empirical action scoring. No bot changes or downloads.

Outcome score (0..100): 60 for surviving lineage at R+10, 30 for retained
longest length, 10 for up to four net new segments. Later splits count through
descendants, but children born before the action do not. Censor final 10 rounds.
This is a declared heuristic, not a causal estimate of unplayed alternatives.
"""
from collections import Counter, defaultdict
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random

from make_dataset import Board, DIRS, DELTAS
from replay_reader import load_replay
from study_strategies import study

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'coaching'
TEAM = 'An IQ too high?'


def context(board, ident, action):
    """Only pre-action 7x7 visibility + own length/count/round/dimensions."""
    return observation_context(board.observation(ident),action)


def observation_context(obs, action):
    tiles = obs['tiles']
    walls = sum(tile[i] == 1 for tile in tiles for i in (3,5,7,9))
    enemies = sum(tile[2] in (3,5) for tile in tiles)
    heads = sum(tile[2] == 5 for tile in tiles)
    pressure = 'many-enemies' if heads >= 2 or enemies >= 8 else 'contact' if enemies else 'quiet'
    terrain = 'walls' if walls >= 24 else 'open'
    phase = 'early' if obs['round'] < 100 else 'middle' if obs['round'] < 350 else 'late'
    length = '2-3' if obs['length'] < 4 else '4-7' if obs['length'] < 8 else '8+'
    count = 'few' if obs['unit_count'] < 6 else 'medium' if obs['unit_count'] < 24 else 'many'
    kind = action['kind']
    if kind == 'split':
        kind = 'split-2' if action['child_length'] == 2 else 'split-large'
    elif kind == 'move':
        steps = action['steps']
        kind = 'sprint' if len(steps) > 1 else 'move'
        if steps:
            d = DIRS.index(steps[0]); edge = tiles[24][3+2*d]
            dx,dy = DELTAS[d]; destination = tiles[24+dx+7*dy]
            if edge == 1: kind += '-wall'
            elif edge == 2: kind += '-portal'
            elif destination[2]: kind += '-occupied'
            elif destination[0]: kind += '-food'
    return [f'{obs["map"][0]}x{obs["map"][1]}', terrain, phase, length, count, pressure, kind]


def family_lengths(actor, action_seq, alive, parents):
    lengths = []
    for ident, length in alive.items():
        current = ident
        while current != actor and current in parents:
            parent, born_seq = parents[current]
            if born_seq <= action_seq:
                break
            current = parent
        if current == actor:
            lengths.append(length)
    return lengths


def outcome_score(before, lengths):
    if not lengths:
        return 0.0
    return 60 + 30 * min(1, max(lengths)/before) + 10 * min(1, max(0,sum(lengths)-before)/4)


def action_samples(path, summary, limit=1500):
    replay = load_replay(path); board = Board(replay['map'])
    rng = random.Random(int(summary['sha256'][:16],16))
    rows, snapshots, parents = [], {}, {}
    seen = 0
    for seq, event in enumerate(replay['events']):
        kind = event['type']
        if kind == 'roundStart' and board.round >= 0:
            snapshots[board.round] = {i:len(d['body']) for i,d in board.dragons.items()}
        elif kind == 'dragonSplit':
            parents[event['child_id']] = (event['parent_id'],seq)
        elif kind == 'dragonAction':
            seen += 1
            slot = len(rows) if len(rows) < limit else rng.randrange(seen)
            if slot < limit:
                dragon = board.dragons[event['id']]
                row = dict(match=summary['match_id'], group=summary['group_id'],
                    map=summary['map_name'], team=dragon['team'],
                    name=summary['teams'][dragon['team']]['name'], id=event['id'],
                    round=board.round, seq=seq, length=len(dragon['body']),
                    context=context(board,event['id'],event['action']), action=event['action'])
                if slot == len(rows): rows.append(row)
                else: rows[slot] = row
        board.apply(event)
    snapshots[board.round] = {i:len(d['body']) for i,d in board.dragons.items()}
    result = []
    for row in rows:
        future = snapshots.get(row['round']+10)
        if future is None: continue  # right censored; never label as death
        lengths = family_lengths(row['id'],row['seq'],future,parents)
        row['score'] = round(outcome_score(row['length'],lengths),3)
        row['alive10'] = bool(lengths)
        row['longest10'] = max(lengths,default=0)
        result.append(row)
    return result


def key(context, detailed=True):
    # Coarse fallback still conditions on visible enemy pressure and action.
    return '|'.join(context if detailed else [context[0],context[1],context[-2],context[-1]])


def fit(rows):
    buckets = defaultdict(lambda: [0,0.0,set()])
    for row in rows:
        for prefix,detailed in [('full:',True),('coarse:',False)]:
            b = buckets[prefix+key(row['context'],detailed)]
            b[0] += 1; b[1] += row['score']; b[2].add(row['group'])
    return {k:dict(n=v[0],mean=v[1]/v[0],groups=len(v[2])) for k,v in buckets.items()}


def predict(model, context):
    for prefix,detailed in [('full:',True),('coarse:',False)]:
        row = model.get(prefix+key(context,detailed))
        if row and row['n'] >= 30 and row['groups'] >= 3:
            return row
    return None


def main():
    OUT.mkdir(exist_ok=True); cache = OUT / 'cache'; cache.mkdir(exist_ok=True)
    matches, samples, seen, match_ids = [], [], {}, set()
    for directory in ('my_replays','top_replays','replays','all_replays'):
        for path in sorted((ROOT/directory).glob('*.replay')):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            meta = json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
            ident = meta.get('match_id')
            if ident in match_ids: continue
            match_ids.add(ident)
            if digest in seen:
                alias = copy.deepcopy(seen[digest])
                alias.update(match_id=ident, group_id=meta['group_id'],
                    path=str(path.relative_to(ROOT.parent)), file=path.name,
                    duplicate_replay_of=seen[digest]['match_id'])
                for side,row in alias['teams'].items():
                    row['name']=meta['team'+side+'Name']
                    row['submission_id']=meta['submission'+side+'Id']
                matches.append(alias)
                continue
            target = cache/(digest+'.json')
            if target.exists():
                data = json.loads(target.read_text(encoding='utf-8'))
            else:
                summary = study(path)
                data = dict(summary=summary, samples=action_samples(path,summary))
                target.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            # Upgrade cached v1 contexts using known map dimensions only.
            for row in data['samples']:
                if len(row['context']) == 6:
                    w,h = data['summary']['map_size']
                    row['context'].insert(0,f'{w}x{h}')
            matches.append(data['summary']); samples.extend(data['samples'])
            seen[digest] = data['summary']
            print(f'Audited {path.name}',flush=True)
    own = [m for m in matches if any(r['name']==TEAM for r in m['teams'].values())]
    own_groups = {m['group_id'] for m in own}
    public_groups = sorted({r['group'] for r in samples} - own_groups)
    # Keep full series and both opponents on one side of this split.
    holdout = {g for i,g in enumerate(public_groups) if i%5 == 0}
    train = [r for r in samples if r['group'] not in own_groups|holdout]
    validation = [r for r in samples if r['group'] in holdout]
    model = fit(train)
    predictions = [(r,predict(model,r['context'])) for r in validation]
    covered = [(r,p) for r,p in predictions if p is not None]
    baseline = sum(r['score'] for r in train)/len(train) if train else 0
    metrics = dict(training_series=len(public_groups)-len(holdout), validation_series=len(holdout),
        own_series_excluded=len(own_groups), train_samples=len(train), validation_samples=len(validation),
        covered=len(covered), mae=sum(abs(r['score']-p['mean']) for r,p in covered)/len(covered) if covered else None,
        baseline_mae=sum(abs(r['score']-baseline) for r,p in covered)/len(covered) if covered else None)
    payload = dict(score_definition=__doc__, feature_version=2, metrics=metrics, buckets=model,
                   train_groups=sorted(set(public_groups)-holdout), validation_groups=sorted(holdout),
                   excluded_own_groups=sorted(own_groups))
    (OUT/'action_model.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'matches.json').write_text(json.dumps(matches,ensure_ascii=False,indent=2),encoding='utf-8')
    with gzip.open(OUT/'scored_actions.jsonl.gz','wt',encoding='utf-8') as f:
        for row in samples:
            row['estimated'] = predict(model,row['context'])
            f.write(json.dumps(row,ensure_ascii=False)+'\n')
    write_reports(matches,own,samples,metrics)
    print(json.dumps(metrics),flush=True)


def write_reports(matches, own, samples, metrics):
    def result(m,side):
        return 'DRAW' if m['result']['winner'] is None else 'WIN' if m['result']['winner']==side else 'LOSS'
    lines = ['# My Battles — An IQ too high?', '',
        f'{len(own)} games / {len({m["group_id"] for m in own})} series, from public team links. '
        'Not a complete private history export. Different submissions are not merged.', '',
        f'{len({m["sha256"] for m in own})} distinct replay contents. Identical replay contents '
        'at different match IDs are retained in the match table but sampled only once for scoring.', '',
        'Death causes below are engine observations. Strategic explanations require counterfactual tests.', '',
        '| Match | Map | Submission | Result / end | Own final units / longest | Enemy final units / longest | Splits own / enemy | Own deaths |',
        '|---|---|---|---|---|---|---|---|']
    bymap = defaultdict(list)
    for m in own:
        side = next(s for s,r in m['teams'].items() if r['name']==TEAM)
        r=m['teams'][side]; enemy=m['teams']['B' if side=='A' else 'A']; a=r['final']; b=enemy['final']
        bymap[m['map_name']].append((m,r,enemy,side))
        deaths=', '.join(f'{k}:{v}' for k,v in r['death_counts'].items())
        lines.append(f'| {m["match_id"]} | {m["map_name"]} | {r["submission_id"]} | '
            f'{result(m,side)} / {m["result"]["end_reason"]} | {a["dragon_count"]} / {a["longest_dragon"]} | '
            f'{b["dragon_count"]} / {b["longest_dragon"]} | {len(r["splits"])} / {len(enemy["splits"])} | {deaths} |')
    for map_name, rows in sorted(bymap.items()):
        lines += ['',f'## {map_name}','']
        for m,r,enemy,side in rows:
            lines.append(f'- Match {m["match_id"]}, {result(m,side)}, vs {enemy["name"]}, '
                f'own submission {r["submission_id"]}; {m["rounds"]} rounds. '
                f'Peak units {r["peak_units"]} vs {enemy["peak_units"]}; '
                f'peak longest {r["peak_longest"]} vs {enemy["peak_longest"]}.')
            if r['deaths']:
                critical=max(r['deaths'],key=lambda d:d['length'])
                last=r['deaths'][-1]
                lines.append(f'  Largest own loss: R{critical["round"]}, dragon {critical["dragon_id"]}, '
                    f'length {critical["length"]}, {critical["reason"]}. '
                    f'Last own death: R{last["round"]}, dragon {last["dragon_id"]}, {last["reason"]}.')
            life=r['child_10_rounds']; other=enemy['child_10_rounds']
            lines.append(f'  Children surviving 10 rounds: {life["survived"]}/{life["eligible"]} '
                f'vs {other["survived"]}/{other["eligible"]}; late splits '
                f'{r["split_phases"].get("350-499",0)} vs {enemy["split_phases"].get("350-499",0)}.')
    (OUT/'my_battles.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=['# Per-map observed strategies','',
           'Descriptive associations, not an optimal policy. Each row is one completed match; '
           'series are correlated and opponents/submissions differ.','',
           '| Map | Match | Winner / submission | End | Peak units | Final units / longest | Split early/middle/late |',
           '|---|---|---|---|---|---|---|']
    for m in sorted(matches,key=lambda x:(x['map_name'],x['match_id'] or 0)):
        side=m['result']['winner']
        if side is None: continue
        r=m['teams'][side]; f=r['final']; ph=r['split_phases']
        lines.append(f'| {m["map_name"]} | {m["match_id"]} | {r["name"]} / {r["submission_id"]} | '
            f'{m["result"]["end_reason"]} | {r["peak_units"]} | {f["dragon_count"]} / {f["longest_dragon"]} | '
            + '/'.join(str(ph.get(p,0)) for p in ('0-99','100-349','350-499'))+' |')
    (OUT/'maps.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=['# Action scoring','',__doc__,'',
        'Uniform deterministic reservoir: up to 1,500 actions per match, both sides, then exclude '
        'the final 10 rounds. Own series are entirely excluded from fitting. '
        'Every fifth sorted public series is validation; no turn-level random split. '
        'Features only use pre-action 7x7 observations and own public state. '
        'Opponent pressure is visible contact, not an inferred hidden source-code strategy.', '',
        'Prediction needs >=30 samples from >=3 training series; otherwise no estimate. '
        'The model estimates outcomes of observed action classes; it cannot prove an unplayed '
        'direction or split would win. Legal-action checking must precede any use in a bot.', '',
        '```json',json.dumps(metrics,indent=2),'```','',
        'The model is an offline review tool, not installed in Leviathan. '
        'An action with a low score may have had no good alternative. '
        'Long-term match victory is not the same objective as this 10-round score.']
    (OUT/'action_scoring.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    reviews = [r for r in samples if r['name']==TEAM]
    reviews.sort(key=lambda r:(r['score'],-r['length']))
    selected, per_match = [], Counter()
    for row in reviews:
        if per_match[row['match']] >= 3: continue
        per_match[row['match']] += 1; selected.append(row)
    (OUT/'review_actions.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Own action review queue','',
        'Up to three lowest hindsight scores per match, preferring longer actors on ties. '
        'This is a sampled review queue, not proof these were avoidable mistakes. '
        'Predicted scores use public training series only; unsupported contexts abstain.', '',
        '| Match | Map | Round / dragon | Length | Action | Context | Hindsight /100 | Public estimate /100 |',
        '|---|---|---|---:|---|---|---:|---|']
    for r in selected:
        estimate=r['estimated']
        prediction=f'{estimate["mean"]:.1f} (n={estimate["n"]}, series={estimate["groups"]})' if estimate else 'insufficient support'
        lines.append(f'| {r["match"]} | {r["map"]} | {r["round"]} / {r["id"]} | {r["length"]} | '
            f'{json.dumps(r["action"])} | {", ".join(r["context"])} | {r["score"]} | {prediction} |')
    (OUT/'review_actions.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
