"""Describe observed play in replays; this does not infer a bot's hidden code."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from download_battles import atomic_write, json_write
from make_dataset import Board
from replay_reader import load_replay


def analyze(path):
    replay = load_replay(path)
    board = Board(replay['map'])
    sidecar = path.with_suffix('.meta.json')
    meta = json.loads(sidecar.read_text(encoding='utf-8')) if sidecar.exists() else {}
    teams = {}
    for team in 'AB':
        teams[team] = {'name': meta.get(f'team{team}Name', replay['bot_'+team]),
                       'turns': 0, 'move_actions': 0, 'sprint_actions': 0,
                       'splits': [], 'sonar_pings': 0, 'deaths': [],
                       'peak_units': 0, 'peak_longest': 0, 'peak_total': 0}
    timeline = []
    max_round = -1

    def lengths(team):
        return [len(d['body']) for d in board.dragons.values() if d['team'] == team]

    def snapshot():
        for team in 'AB':
            values = lengths(team)
            timeline.append({'round': board.round, 'team': team, 'units': len(values),
                             'longest': max(values, default=0), 'total_length': sum(values)})

    for event in replay['events']:
        kind = event['type']
        if kind == 'roundStart':
            if board.round >= 0:
                snapshot()
            max_round = event['round']
        if kind in ('turnStart', 'dragonAction', 'dragonDeath'):
            d = board.dragons[event['id']]
            row = teams[d['team']]
            if kind == 'turnStart':
                row['turns'] += 1
            elif kind == 'dragonAction' and event['action']['kind'] == 'move':
                row['move_actions'] += 1
                row['sprint_actions'] += len(event['action']['steps']) > 1
            elif kind == 'dragonDeath':
                row['deaths'].append({'round': board.round, 'dragon_id': event['id'],
                                      'length': len(d['body']), 'reason': event['reason']})
        elif kind == 'dragonSplit':
            row = teams[event['team']]
            row['splits'].append({'round': board.round, 'parent_id': event['parent_id'],
                                  'length_before': len(board.dragons[event['parent_id']]['body']),
                                  'child_length': len(event['child_body'])})
        elif kind == 'sonarPing':
            sender = board.dragons.get(event['sender_id'])
            if sender:
                teams[sender['team']]['sonar_pings'] += 1
        board.apply(event)
        if kind in ('dragonUpdate', 'dragonSplit', 'dragonDeath'):
            for team in 'AB':
                values = lengths(team)
                row = teams[team]
                row['peak_units'] = max(row['peak_units'], len(values))
                row['peak_longest'] = max(row['peak_longest'], max(values, default=0))
                row['peak_total'] = max(row['peak_total'], sum(values))
    snapshot()
    for team in 'AB':
        values = lengths(team)
        final = {'dragon_count': len(values), 'longest_dragon': max(values, default=0),
                 'total_length': sum(values)}
        if final != replay['result'][team]:
            raise ValueError(f'{path.name}: reconstructed final standing mismatch')
        teams[team]['final'] = final
        teams[team]['death_counts'] = dict(Counter(d['reason'] for d in teams[team]['deaths']))
    return {'file': path.name, 'match_id': meta.get('match_id'),
            'group_id': meta.get('group_id', hashlib.sha256(path.read_bytes()).hexdigest()),
            'source_url': meta.get('source_url'), 'map_name': meta.get('mapName', 'unknown'),
            'map_size': [board.w, board.h], 'rounds': max_round+1,
            'result': replay['result'], 'teams': teams, 'timeline': timeline}


def markdown(matches):
    def esc(s):
        return str(s).replace('|', '\\|').replace('\n', ' ')
    lines = ['# Phân tích replay Top Battles', '',
             f'Thời điểm phân tích (UTC): {datetime.now(timezone.utc).isoformat()}', '',
             f"{len(matches)} trận; {len({m['group_id'] for m in matches})} nhóm series/match; "
             f"{len({t['name'] for m in matches for t in m['teams'].values()})} tên đội.", '',
             'Mỗi hàng là một đội trong một trận. Sprint = lượt yêu cầu MOVE nhiều bước; '
             'split = sự kiện tách thành công. R ở bảng là vòng đếm từ 0. '
             'Đây là mô tả hành vi, không phải bằng chứng một chiến thuật gây ra chiến thắng.', '',
             '| Match | Map | Đội | Kết quả | Số vòng | Split | Split đầu (R / độ dài trước) | Sprint / MOVE | Sonar | Rồng tối đa | Dài nhất cuối | Tổng dài cuối |',
             '|---|---|---|---|---:|---:|---|---|---:|---:|---:|---:|']
    for m in matches:
        for team, row in m['teams'].items():
            win = m['result']['winner']
            outcome = 'Hòa' if win is None else 'Thắng' if win == team else 'Thua'
            first = row['splits'][0] if row['splits'] else None
            split = f"{first['round']} / {first['length_before']}" if first else '—'
            ident = m['match_id'] or m['file']
            if m['source_url']:
                ident = f"[{ident}]({m['source_url']})"
            lines.append('| ' + ' | '.join(map(esc, [ident, m['map_name'], row['name'], outcome,
                         m['rounds'], len(row['splits']), split,
                         f"{row['sprint_actions']} / {row['move_actions']}", row['sonar_pings'],
                         row['peak_units'], row['final']['longest_dragon'], row['final']['total_length']])) + ' |')
    lines += ['', '## Các điểm cần xem lại trong viewer', '',
              'Xem 5–10 vòng trước khi tách, sprint hoặc chết. So sánh vùng nhìn, lối thoát, '
              'pearl và vị trí đối thủ; không suy chiến thuật chỉ từ kết quả cuối.', '']
    for m in matches:
        lines.append(f"- Match {m['match_id'] or m['file']} ({m['map_name']}):")
        for team, row in m['teams'].items():
            reasons = ', '.join(f'{key}: {value}' for key, value in row['death_counts'].items()) or 'không có'
            lines.append(f"  - {row['name']} ({team}): số lần chết — {reasons}.")
    lines += ['', '## Cách sử dụng', '',
              '- Giữ cả thắng và thua để nghiên cứu điểm mạnh và cách khắc chế.',
              '- Kiểm tra giả thuyết bằng bot đã sửa đối đầu bot gốc trên cùng map, seed và cả hai phía.',
              '- Để các trận cùng series trong cùng tập train/validation/test. 10 trận có thể chỉ là 2 series.',
              '- Kết quả/đối thủ/toàn bản đồ trong báo cáo chỉ phục vụ phân tích; không dùng làm input bot ngoài vision.',
              '- File JSON đi kèm chứa từng split, từng lần chết và timeline theo vòng để phân tích sâu hơn.', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--out', type=Path, default=Path('top_analysis'))
    args = p.parse_args()
    files = sorted(args.directory.rglob('*.replay'))
    if not files:
        p.error('No replay files found')
    matches, seen = [], set()
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        row = analyze(path)
        if row['result']['terminated']:
            matches.append(row)
        print(f'Analyzed {path.name}', flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    json_write(args.out / 'report.json', matches)
    atomic_write(args.out / 'report.md', markdown(matches).encode('utf-8'))
    print(f"Written {args.out / 'report.md'} and report.json", flush=True)


if __name__ == '__main__':
    main()
