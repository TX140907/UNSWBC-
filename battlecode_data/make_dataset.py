"""Replay -> pre-action observations and action labels (JSONL/gzip)."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

from replay_reader import load_replay

DIRS = 'NESW'
DELTAS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


class Board:
    def __init__(self, text):
        self.dragons = {}
        self.pearls = set()
        self.countdowns = {}
        self.edges = {}
        self.inboxes = defaultdict(list)
        self.round = -1
        self.unit_limit = 64
        for line in text.splitlines():
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            p = line.split()
            if p[0] == 'MAP':
                self.w, self.h = map(int, p[1:3])
                if not (7 <= self.w <= 64 and 7 <= self.h <= 64):
                    raise ValueError('Unsupported map dimensions')
            elif p[0] == 'UNIT_LIMIT':
                self.unit_limit = int(p[1])
            elif p[0] == 'TILE':
                x, y, lo, hi = map(int, p[1:])
                self.countdowns[x, y] = -1 if hi == 0 else None
            elif p[0] == 'EDGE':
                edge_id, kind, portal = map(int, p[1:])
                row, x = divmod(edge_id, self.w+1)
                key = ('H' if row % 2 == 0 else 'V', x % self.w, (row//2) % self.h)
                if key in self.edges and self.edges[key] != [kind, portal]:
                    raise ValueError('Inconsistent wrapped map edges')
                self.edges[key] = [kind, portal]
            elif p[0] in ('DRAGON', 'SNAKE'):
                team, n, *coords = map(int, p[1:])
                body = [coords[i:i+2] for i in range(0, len(coords), 2)]
                if len(body) != n or n < 2:
                    raise ValueError('Bad initial dragon')
                head, neck = body[:2]
                dx, dy = (head[0]-neck[0]) % self.w, (head[1]-neck[1]) % self.h
                facing = 'E' if dx == 1 else 'W' if dx == self.w-1 else 'S' if dy == 1 else 'N' if dy == self.h-1 else 'E'
                self.dragons[len(self.dragons)] = {'team': 'AB'[team], 'facing': facing, 'body': body}

    def edge(self, x, y, direction):
        key = [('H', x, y), ('V', (x+1) % self.w, y),
               ('H', x, (y+1) % self.h), ('V', x, y)][direction]
        return self.edges.get(key, [0, -1])

    def observation(self, dragon_id):
        me = self.dragons[dragon_id]
        hx, hy = me['body'][0]
        occupied = {}
        # Encode only segments actually in the 7x7 view below.
        for ident, dragon in self.dragons.items():
            for i, pos in enumerate(dragon['body']):
                code = (6 if i == 0 else 1) if ident == dragon_id else (
                    (4 if i == 0 else 2) if dragon['team'] == me['team'] else (5 if i == 0 else 3))
                occupied[tuple(pos)] = code
        tiles = []
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                x, y = (hx+dx) % self.w, (hy+dy) % self.h
                countdown = self.countdowns.get((x, y), -1)
                if countdown is None:
                    raise ValueError('Missing initial pearl countdown in replay')
                row = [int((x, y) in self.pearls), countdown, occupied.get((x, y), 0)]
                for d in range(4):
                    row.extend(self.edge(x, y, d))
                tiles.append(row)
        return {'round': self.round, 'position': [hx, hy], 'map': [self.w, self.h],
                'length': len(me['body']), 'facing': me['facing'],
                'unit_count': sum(d['team'] == me['team'] for d in self.dragons.values()),
                'unit_limit': self.unit_limit, 'sonar': list(self.inboxes[dragon_id]),
                'tiles': tiles}

    def apply(self, e):
        kind = e['type']
        if kind == 'roundStart':
            if e['round'] != self.round+1:
                raise ValueError('Non-consecutive rounds')
            self.round = e['round']
            for pos, count in self.countdowns.items():
                if count is not None and count >= 0:
                    self.countdowns[pos] = count-1
        elif kind == 'pearlCountdown':
            self.countdowns[tuple(e['tile'])] = e['countdown']
        elif kind == 'tileChange':
            if e['has_pearl']:
                self.pearls.add(tuple(e['tile']))
            else:
                self.pearls.discard(tuple(e['tile']))
        elif kind == 'dragonUpdate':
            dragon = self.dragons[e['id']]
            dragon['facing'] = e['facing']
            # Init events publish the current pose without moving the head.
            if dragon['body'][0] != e['head']:
                dragon['body'].insert(0, e['head'])
            while len(dragon['body']) > 1 and dragon['body'][-1] != e['tail']:
                dragon['body'].pop()
            if dragon['body'][-1] != e['tail']:
                raise ValueError('Replay tail inconsistent with reconstructed body')
        elif kind == 'dragonSplit':
            parent = self.dragons[e['parent_id']]
            parent['body'] = e['parent_body']
            self.dragons[e['child_id']] = {'team': e['team'], 'facing': e['facing'], 'body': e['child_body']}
        elif kind == 'dragonDeath':
            self.dragons.pop(e['id'], None)
            self.inboxes.pop(e['id'], None)
        elif kind == 'sonarPing' and e['hit_id'] is not None:
            self.inboxes[e['hit_id']].append(e['value'])


def samples(replay):
    board = Board(replay['map'])
    pending = None
    sample = None
    for e in replay['events']:
        if e['type'] in ('turnStart', 'roundStart'):
            if sample is not None:
                yield sample
                sample = None
            pending = None
        if e['type'] == 'turnStart':
            ident = e['id']
            pending = (ident, board.dragons[ident]['team'], board.observation(ident))
            board.inboxes[ident].clear()
        elif e['type'] == 'dragonAction':
            if pending is None or pending[0] != e['id']:
                raise ValueError('Action without matching turnStart')
            ident, team, obs = pending
            sample = {'dragon_id': ident, 'team': team, 'observation': obs,
                      'action': e['action'], 'died_this_turn': False, 'death_reason': None}
        elif e['type'] == 'dragonDeath' and sample is not None and e['id'] == sample['dragon_id']:
            sample['died_this_turn'] = True
            sample['death_reason'] = e['reason']
        board.apply(e)
    if sample is not None:
        yield sample
    for team in 'AB':
        lengths = [len(d['body']) for d in board.dragons.values() if d['team'] == team]
        reconstructed = {'dragon_count': len(lengths), 'longest_dragon': max(lengths, default=0), 'total_length': sum(lengths)}
        if reconstructed != replay['result'][team]:
            raise ValueError('Reconstructed final standings differ from replay result')


def split_for(group):
    # Every turn of the same match (or supplied series group) has one split.
    value = int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 100
    return 'train' if value < 80 else 'validation' if value < 90 else 'test'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--output', type=Path, default=Path('dataset.jsonl.gz'))
    p.add_argument('--winners-only', action='store_true')
    args = p.parse_args()
    files = sorted(args.directory.rglob('*.replay'))
    if not files:
        p.error('No .replay files found')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name+'.part')
    opener = gzip.open if args.output.suffix == '.gz' else open
    seen = set()
    totals = Counter()
    try:
        with opener(temporary, 'wt', encoding='utf-8') as out:
            for path in files:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                replay = load_replay(path)
                if not replay['result']['terminated']:
                    totals['unfinished_files'] += 1
                    continue
                meta_file = path.with_suffix('.meta.json')
                meta = json.loads(meta_file.read_text(encoding='utf-8')) if meta_file.exists() else {}
                group = str(meta.get('group_id') or digest)
                split = split_for(group)
                for sample in samples(replay):
                    team = sample['team']
                    if args.winners_only and replay['result']['winner'] != team:
                        continue
                    sample.update(match_sha256=digest, group_id=group, split=split,
                                  source_file=path.name, bot_name=replay['bot_'+team],
                                  team_won=replay['result']['winner'] == team)
                    out.write(json.dumps(sample, separators=(',', ':'), ensure_ascii=False)+'\n')
                    totals['samples'] += 1
                    totals[split] += 1
                totals['matches'] += 1
                print(f'Converted {path.name}')
        temporary.replace(args.output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(json.dumps(dict(totals), indent=2))
    print(f'Written: {args.output}')


if __name__ == '__main__':
    main()
