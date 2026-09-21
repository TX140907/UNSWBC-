"""Challenge teams within +/-12 ranks, unranked, at most 10 games per invocation.

From repository root:
  python battlecode_data/challenge_cycle.py run
  python battlecode_data/challenge_cycle.py status
  python battlecode_data/download_battles.py --ids-file battlecode_data/experiments/128/battle_ids.txt --out battlecode_data/replays

Use plan instead of run to preview without POST. Reuses download_battles.Client
and its UNSWBC_API_KEY / hidden prompt convention. Only creates battles; does not
upload, activate, or train bot code. Battles use the currently active server bot.

API contract: https://game.battlecode.au/docs/api. Credentials stay in memory.
Unknown response schemas fail closed. POST is never retried automatically.
"""
import argparse
from contextlib import contextmanager
import getpass
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

from download_battles import Client, BASE, DownloadError, json_write, recent_rows, api_key

ROOT = Path(__file__).resolve().parent
TERMINAL = {'completed', 'failed', 'cancelled', 'canceled'}
PENDING = {'pending', 'queued', 'running', 'building', 'processing'}


def rows(payload, names):
    if isinstance(payload, list):
        if all(isinstance(r, dict) for r in payload):
            return payload
    elif isinstance(payload, dict):
        for name in names:
            if name in payload:
                return rows(payload[name], names)
    raise DownloadError('Unrecognized API list schema; no challenges sent')


def positive(value):
    if isinstance(value, bool) or not str(value).isdigit() or int(value) <= 0:
        raise DownloadError('Expected a positive API ID/rank')
    return int(value)


def team_id(row):
    team = row.get('team', row)
    return positive(team.get('id', row.get('teamId')))


def ladder(payload):
    result = []
    for r in rows(payload, ('leaderboard', 'teams', 'ratings', 'data')):
        team = r.get('team', r)
        if r.get('ranked') is False or team.get('hasBot') is False:
            continue
        # Do not equate response order with rank: the API must supply it.
        result.append(dict(id=team_id(r), rank=positive(r.get('rank', team.get('rank'))),
                           name=str(team.get('name', r.get('teamName', '')))))
    if len({r['id'] for r in result}) != len(result):
        raise DownloadError('Duplicate team IDs in leaderboard')
    return result


def battle_games(payload):
    if not isinstance(payload, dict):
        raise DownloadError('Unrecognized battle detail schema')
    if isinstance(payload.get('match'), dict):
        match = payload['match']
        games = payload.get('games') or [match]
        return [dict(match, **g) for g in games]
    for key in ('battle', 'data'):
        if isinstance(payload.get(key), dict):
            return battle_games(payload[key])
    if isinstance(payload.get('games'), list) and payload['games']:
        return payload['games']
    if 'teamAId' in payload and 'teamBId' in payload:
        return [payload]
    raise DownloadError('Battle has no recognizable games/teams; stop to avoid duplicate challenges')


def opponent(game, own):
    a, b = positive(game.get('teamAId')), positive(game.get('teamBId'))
    if own not in (a, b) or a == b:
        raise DownloadError('Battle does not belong to configured team')
    return b if own == a else a


def pending_teams(client, own):
    blocked = set()
    for row in recent_rows(client.json('battles?limit=200')):
        detail = client.json(f'battles/{positive(row.get("id", row.get("battleId")))}')
        for g in battle_games(detail):
            other = opponent(g, own)
            status = g.get('status')
            if status not in TERMINAL | PENDING:
                raise DownloadError('Unknown game status; stop before POST')
            if status in PENDING:
                blocked.add(other)
    return blocked


def select_targets(teams, own, maps, history, blocked, radius=12, limit=10):
    if not 1 <= limit <= 10 or not 0 <= radius <= 50:
        raise DownloadError('Use 1-10 games and rank radius 0-50')
    mine = next((r for r in teams if r['id'] == own), None)
    if mine is None:
        raise DownloadError('Your team is not ranked on this leaderboard')
    available = [r for r in teams if r['id'] != own and r['id'] not in blocked
                 and abs(r['rank'] - mine['rank']) <= radius]
    counts = {}
    for h in history:
        if h['status'] != 'rejected':
            key = (h['team_id'], h['map_id'])
            counts[key] = counts.get(key, 0) + 1
    available.sort(key=lambda r: (sum(v for (t, _), v in counts.items() if t == r['id']),
                                  abs(r['rank']-mine['rank']), r['rank'], r['id']))
    selected = []
    coverage = {m['id']: sum(v for (_, mid), v in counts.items() if mid == m['id']) for m in maps}
    for r in available[:limit]:
        m = min(maps, key=lambda m: (counts.get((r['id'], m['id']), 0), coverage[m['id']], m['id']))
        selected.append(dict(team_id=r['id'], team_name=r['name'], rank=r['rank'],
                             map_id=m['id'], map_name=m['name']))
        coverage[m['id']] += 1
    return selected


class UnknownPost(DownloadError):
    """The server may have accepted this challenge. Do not retry."""


def post_battle(client, target):
    body = json.dumps(dict(teamId=target['team_id'], ranked=False,
                           mapIds=[target['map_id']])).encode()
    req = urllib.request.Request(BASE+'battles', data=body, method='POST', headers={
        'Authorization': 'Bearer '+client.key, 'Origin': 'https://game.battlecode.au',
        'Content-Type': 'application/json', 'User-Agent': 'unswbc-challenge-cycle/1.0'})
    time.sleep(max(0, client.last_request + 0.65 - time.monotonic()))
    client.last_request = time.monotonic()
    try:
        with client.opener.open(req, timeout=30) as response:
            payload = json.loads(response.read(1024*1024))
        ids = payload.get('ids')
        if not isinstance(ids, list) or len(ids) != 1:
            raise UnknownPost('Unexpected POST result; inspect My Battles before retrying')
        return [positive(i) for i in ids]
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            retry_after=max(1,float(e.headers.get('Retry-After','60')))
        except (TypeError,ValueError):
            retry_after=60
        e.close()
        if status in (400, 401, 403, 404, 409, 422, 429):
            error=DownloadError(f'POST rejected (HTTP {status}); not accepted', status)
            error.retry_after=retry_after
            raise error from None
        raise UnknownPost(f'POST outcome uncertain (HTTP {status}); no retry') from None
    except (urllib.error.URLError, OSError, TimeoutError, ValueError, AttributeError):
        raise UnknownPost('POST outcome uncertain; inspect My Battles, no retry') from None
    except DownloadError as e:
        if isinstance(e, UnknownPost):
            raise
        raise UnknownPost('Invalid POST response; inspect My Battles, no retry') from None


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory/'cycle.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise DownloadError(f'Another cycle is running (or stale lock): {lock}') from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def load_state(directory, own):
    path = directory/'state.json'
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(team_id=own, attempts=[])
    if state['team_id'] != own:
        raise DownloadError('State belongs to another team')
    return state


def reserve(state, target, now):
    # Count uncertain requests against the hourly budget too, including after restart.
    if any(a['status'] in ('submitting', 'uncertain') for a in state['attempts']):
        raise DownloadError('An earlier POST has uncertain outcome. Attach its battle ID before sending more.')
    used = sum(a['status'] != 'rejected' and a['created'] > now-3600 for a in state['attempts'])
    if used >= 60:
        raise DownloadError('Local 60 games/hour budget reached; run later')
    entry = dict(target, attempt_id=uuid.uuid4().hex, created=now, status='submitting', ids=[])
    state['attempts'].append(entry)
    return entry


def prepare(client, state, radius, limit):
    identity = client.json('team')
    if team_id(identity) != state['team_id']:
        raise DownloadError('API key belongs to another team')
    teams = ladder(client.json('leaderboard'))
    maps = [dict(id=positive(m['id']), name=str(m['name']))
            for m in rows(client.json('maps'), ('maps', 'data')) if m.get('active', True)]
    if not maps or len({m['id'] for m in maps}) != len(maps):
        raise DownloadError('Missing or duplicate maps')
    blocked = pending_teams(client, state['team_id'])
    blocked.update(a['team_id'] for a in state['attempts']
                   if a['status'] in ('submitting', 'uncertain', 'submitted'))
    return dict(created=time.time(), team_id=state['team_id'], ranked=False,
                radius=radius, max_games=limit,
                targets=select_targets(teams, state['team_id'], maps, state['attempts'], blocked, radius, limit))


def refresh(client, state, directory):
    for entry in state['attempts']:
        if entry['status'] != 'submitted':
            continue
        complete = True
        failed = False
        for ident in entry['ids']:
            detail = client.json(f'battles/{ident}')
            json_write(directory/f'battle_{ident}.json', detail)
            games = battle_games(detail)
            if len(games) != 1:
                raise DownloadError('Expected one unranked game')
            g = games[0]
            if opponent(g, state['team_id']) != entry['team_id'] or positive(g['mapId']) != entry['map_id']:
                raise DownloadError('Battle team/map differs from request')
            status = g.get('status')
            if status not in TERMINAL | PENDING:
                raise DownloadError('Unknown battle status')
            complete = complete and status in TERMINAL
            failed = failed or status in TERMINAL - {'completed'}
        if complete:
            entry['status'] = 'failed' if failed else 'completed'
    json_write(directory/'state.json', state)
    export_ids(state, directory)


def export_ids(state, directory):
    ids = sorted({i for a in state['attempts'] for i in a['ids']})
    (directory/'battle_ids.txt').write_text(''.join(str(i)+'\n' for i in ids), encoding='utf-8')


def attach(client, state, attempt_id, battle_id):
    entry = next((a for a in state['attempts'] if a['attempt_id'] == attempt_id), None)
    if entry is None or entry['status'] not in ('submitting', 'uncertain'):
        raise DownloadError('Attempt is not unresolved')
    if any(battle_id in a['ids'] for a in state['attempts']):
        raise DownloadError('Battle already attached')
    games = battle_games(client.json(f'battles/{battle_id}'))
    if len(games) != 1:
        raise DownloadError('Expected one unranked game')
    g = games[0]
    if (opponent(g, state['team_id']) != entry['team_id'] or
            positive(g['mapId']) != entry['map_id'] or g.get('ranked') is not False):
        raise DownloadError('Battle does not match this unranked request')
    entry.update(ids=[battle_id], status='submitted')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['plan', 'run', 'status', 'attach'], nargs='?', default='plan')
    p.add_argument('--team-id', type=int, default=128)
    p.add_argument('--radius', type=int, default=12)
    p.add_argument('--games', type=int, default=10)
    p.add_argument('--attempt')
    p.add_argument('--battle-id', type=int)
    args = p.parse_args()
    if not 1 <= args.games <= 10 or not 0 <= args.radius <= 50 or args.team_id <= 0:
        p.error('Use positive team ID, 1-10 games and radius 0-50')
    # One canonical ledger per team so different working directories share quota/lock.
    directory = ROOT/'experiments'/str(args.team_id)
    key = api_key()
    if not key.strip():
        p.error('Missing API key')
    client = Client(key.strip())
    try:
        with locked(directory):
            state = load_state(directory, args.team_id)
            if args.command == 'attach':
                if not args.attempt or not args.battle_id:
                    p.error('attach needs --attempt and --battle-id')
                attach(client, state, args.attempt, positive(args.battle_id))
                json_write(directory/'state.json', state)
                export_ids(state, directory)
            elif args.command == 'status':
                refresh(client, state, directory)
            else:
                # Refresh completed previous requests before selecting a new cohort.
                refresh(client, state, directory)
                print('Reading leaderboard, maps and pending battles...', flush=True)
                plan = prepare(client, state, args.radius, args.games)
                json_write(directory/'plan.json', plan)
                for t in plan['targets']:
                    print(f'Rank {t["rank"]}: team {t["team_id"]} / {t["map_name"]}', flush=True)
                if args.command == 'run':
                    for target in plan['targets']:
                        entry = reserve(state, target, time.time())
                        json_write(directory/'state.json', state)  # durable before network side effect
                        try:
                            entry['ids'] = post_battle(client, target)
                            entry['status'] = 'submitted'
                        except UnknownPost:
                            entry['status'] = 'uncertain'
                            raise
                        except DownloadError:
                            entry['status'] = 'rejected'
                            raise
                        finally:
                            json_write(directory/'state.json', state)
                            export_ids(state, directory)
                        print(f'Submitted team {target["team_id"]}: {entry["ids"]}', flush=True)
                else:
                    print('Plan only; no POST sent. Use run to challenge.')
        print(f'State: {directory}; battle_ids.txt can be passed to download_battles.py --ids-file.')
    except (DownloadError, KeyError, TypeError, ValueError) as e:
        # Do not print raw server bodies, keys or signed download links.
        message = str(e) if isinstance(e, DownloadError) else 'Unsupported API/state schema; stopped. No automatic retry.'
        p.exit(1, message+'\n')


if __name__ == '__main__':
    main()
