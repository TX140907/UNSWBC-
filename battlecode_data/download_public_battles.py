"""Download public replays from Top Battles, All Battles, or both.

No API key is required. Follow actual page links and expand completed games
within each series. Pages and match count are bounded by CLI arguments.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
from itertools import islice
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urljoin, urlsplit

from download_battles import DownloadError, json_write
from download_top_battles import ORIGIN, TOP_URL, PublicClient, download_one, top_rows


class Links(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get('href')
        if tag == 'a' and href:
            url = urljoin(self.base_url, href)
            p = urlsplit(url)
            if p.scheme == 'https' and p.netloc == 'game.battlecode.au':
                self.links.append(url)


def listing(html, url, page):
    parser = Links(url)
    parser.feed(html)
    series, next_url = [], None
    for link in parser.links:
        p = urlsplit(link)
        if re.fullmatch(r'/battles/[1-9]\d*', p.path):
            series.append(link)
        elif p.path == '/battles' and parse_qs(p.query).get('page') == [str(page+1)]:
            next_url = link
    series = list(dict.fromkeys(series))
    if not series and not re.search(r'\btotal:\s*0\b', html):
        raise DownloadError('No battle links found; website format may have changed')
    return series, next_url


def completed_games(html):
    # This exact scalar-only list is part of the viewer's public page data.
    # Do not evaluate the surrounding JavaScript.
    m = re.search(r'\bgames:\s*\[(.*?)\]', html, re.S)
    if not m:
        raise DownloadError('Series game list missing; website format may have changed')
    body = m.group(1).strip()
    if not body:
        return []
    blocks = re.findall(r'\{([^{}]*)\}', body)
    if not blocks:
        raise DownloadError('Unrecognized series game list')
    ids = []
    for block in blocks:
        ident = re.search(r'\bid:\s*([1-9]\d*)\b', block)
        status = re.search(r'\bstatus:\s*("(?:\\.|[^"\\])*")', block)
        if not ident or not status:
            raise DownloadError('Unrecognized game ID/status')
        if json.loads(status.group(1)) == 'completed':
            ids.append(int(ident.group(1)))
    return list(dict.fromkeys(ids))


def discover(client, source, pages, start_page=1):
    seen_matches, seen_series = set(), set()
    if source in ('top', 'both'):
        html = client.get(TOP_URL).decode('utf-8')
        for row in top_rows(html):
            ident = row['match_id']
            seen_matches.add(ident)
            yield {'match_id': ident, 'discovered_from': TOP_URL}
    if source in ('all', 'both'):
        url = ORIGIN + '/battles'
        if start_page > 1:
            url += f'?page={start_page}'
        for page in range(start_page, start_page+pages):
            if url is None:
                break
            print(f'Reading All Battles page {page}', flush=True)
            html = client.get(url).decode('utf-8')
            links, next_url = listing(html, url, page)
            for link in links:
                if link in seen_series:
                    continue
                seen_series.add(link)
                # /battles/ID redirects to the viewer for the series.
                for ident in completed_games(client.get(link).decode('utf-8')):
                    if ident not in seen_matches:
                        seen_matches.add(ident)
                        yield {'match_id': ident, 'discovered_from': url,
                               'series_page': link}
            url = next_url


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', choices=('top', 'all', 'both'), default='both')
    p.add_argument('--pages', type=int, default=3, help='Maximum All Battles listing pages to read')
    p.add_argument('--start-page', type=int, default=1)
    p.add_argument('--limit', type=int, default=100, help='Maximum unique completed games considered, including saved files')
    p.add_argument('--out', type=Path, default=Path('replays'))
    p.add_argument('--list-only', action='store_true', help='Save discovered IDs without downloading replay binaries')
    args = p.parse_args()
    if min(args.pages, args.start_page, args.limit) < 1:
        p.error('--pages, --start-page and --limit must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    index = args.out / f'public_index_{stamp}.json'
    rows = []
    totals = {'downloaded': 0, 'already_saved': 0, 'failed': 0}
    client = PublicClient()
    try:
        candidates = discover(client, args.source, args.pages, args.start_page)
        for row in islice(candidates, args.limit):
            rows.append(row)
            ident = row['match_id']
            if args.list_only:
                print(f'Found completed game {ident}', flush=True)
                continue
            try:
                meta, downloaded = download_one(client, ident, args.out)
                key = 'downloaded' if downloaded else 'already_saved'
                totals[key] += 1
                row['status'] = key
                row['group_id'] = meta['group_id']
                print(f"{key}: {ident} / {meta['mapName']} / {meta['teamAName']} vs {meta['teamBName']}", flush=True)
            except (DownloadError, ValueError) as error:
                row['status'] = 'failed'
                totals['failed'] += 1
                print(f'Match {ident}: {error}', flush=True)
                if isinstance(error, DownloadError) and error.status in (401, 403, 429):
                    raise
        print(f'Finished: {len(rows)} unique completed games; {totals}; directory: {args.out}', flush=True)
        if totals['failed']:
            p.exit(1)
    except DownloadError as error:
        p.exit(1, str(error)+'\n')
    finally:
        json_write(index, {'source': args.source, 'start_page': args.start_page,
                          'page_limit': args.pages, 'match_limit': args.limit,
                          'created_utc': stamp, 'matches': rows, 'totals': totals})


if __name__ == '__main__':
    main()
