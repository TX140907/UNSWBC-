"""Download completed games linked on a public team page (not private history)."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

from download_top_battles import PublicClient, ORIGIN, download_one
from download_public_battles import Links, completed_games
from download_battles import json_write


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--team-id', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.team_id <= 0:
        p.error('team-id must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    client = PublicClient()
    url = f'{ORIGIN}/teams/{args.team_id}'
    html = client.get(url).decode('utf-8')
    links = Links(url); links.feed(html)
    series = list(dict.fromkeys(x for x in links.links if re.fullmatch(ORIGIN + r'/battles/\d+', x)))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    manifest = dict(team_id=args.team_id, source=url, series=series, matches=[],
                    scope='Only links on the public team page; not a complete private My Battles export.')
    seen = set()
    try:
        for link in series:
            for ident in completed_games(client.get(link).decode('utf-8')):
                if ident in seen:
                    continue
                seen.add(ident)
                meta, fresh = download_one(client, ident, args.out)
                if args.team_id not in (meta['teamAId'], meta['teamBId']):
                    raise ValueError('Linked match does not include requested team')
                manifest['matches'].append(dict(match_id=ident, group_id=meta['group_id'], fresh=fresh))
                print(f'{ident}: {meta["mapName"]}, {meta["teamAName"]} vs {meta["teamBName"]}', flush=True)
    finally:
        json_write(args.out / f'team_index_{stamp}.json', manifest)
    print(f'Finished: {len(seen)} completed games from {len(series)} linked series.', flush=True)


if __name__ == '__main__':
    main()
