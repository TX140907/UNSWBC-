"""Download public Top Battles replays, without an API key or browser cookies.

Uses links in the actual public page and the same replay route as its viewer.
Verified against the website on 2026-09-21; stop if the website format changes.
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import gzip
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import Request, build_opener

from download_battles import DownloadError, NoRedirect, atomic_write, json_write, valid_id
from replay_reader import load_replay

ORIGIN = 'https://game.battlecode.au'
TOP_URL = ORIGIN + '/top-battles'


class PublicClient:
    def __init__(self):
        self.opener = build_opener(NoRedirect())
        self.last_request = 0.0

    def get(self, url, max_bytes=4*1024*1024):
        redirects = retries = 0
        while True:
            p = urlsplit(url)
            if p.scheme != 'https' or not p.hostname or p.username or p.password:
                raise DownloadError('Invalid HTTPS URL')
            time.sleep(max(0, self.last_request + 1.1 - time.monotonic()))
            self.last_request = time.monotonic()
            # No credentials are used, including when following storage redirects.
            request = Request(url, headers={'User-Agent': 'unswbc-top-battles/1.0'})
            try:
                with self.opener.open(request, timeout=30) as response:
                    data = response.read(max_bytes + 1)
                    encoding = response.headers.get('Content-Encoding', '').lower()
                if len(data) > max_bytes:
                    raise DownloadError('Response exceeds size limit')
                # Browsers transparently decode HTTP gzip; urllib does not.
                if encoding == 'gzip' or data.startswith(b'\x1f\x8b'):
                    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                        data = stream.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        raise DownloadError('Decoded response exceeds size limit')
                return data
            except HTTPError as error:
                code, headers = error.code, error.headers
                error.close()
                if code in (301, 302, 303, 307, 308) and redirects < 5 and headers.get('Location'):
                    url = urljoin(url, headers['Location'])
                    redirects += 1
                    continue
                if code in (429, 500, 502, 503, 504) and retries < 3:
                    delay = 2**(retries+1)
                    value = headers.get('Retry-After')
                    if value:
                        try:
                            delay = max(delay, float(value))
                        except ValueError:
                            try:
                                delay = max(delay, (parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
                            except (ValueError, TypeError):
                                pass
                    if delay > 30:
                        raise DownloadError('Server requests a longer wait; run again later', code) from None
                    print(f'HTTP {code}: retry after {delay:.0f}s', flush=True)
                    time.sleep(delay)
                    retries += 1
                    continue
                raise DownloadError(f'HTTP {code}; stop or use the website Download replay button', code) from None
            except (URLError, OSError, TimeoutError):
                raise DownloadError('Network error; run again later') from None


class TopLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        self.current = None
        p = urlsplit(urljoin(TOP_URL, dict(attrs).get('href', '')))
        if p.scheme == 'https' and p.netloc == 'game.battlecode.au' and p.path == '/visualiser':
            values = parse_qs(p.query).get('match', [])
            if len(values) == 1 and values[0].isdecimal():
                self.current = {'match_id': valid_id(values[0]), 'label_parts': []}

    def handle_data(self, value):
        if self.current is not None and value.strip():
            self.current['label_parts'].append(value.strip())

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            row = self.current
            row['label'] = ' '.join(row.pop('label_parts'))
            self.rows.append(row)
            self.current = None


def top_rows(html):
    parser = TopLinks()
    parser.feed(html)
    rows = list({r['match_id']: r for r in parser.rows}.values())
    if not rows:
        raise DownloadError('No Watch replay links found; page may have changed or require browser access')
    return rows


def match_metadata(html, match_id):
    # Parse only scalar literals in the server-rendered data; never execute JS.
    marker = re.search(r'\bbattle:\s*\{\s*match:\s*\{', html)
    if marker is None:
        raise DownloadError('Match metadata not found; website format changed')
    block = html[marker.end():]
    block = re.split(r'\},\s*games:', block, maxsplit=1)[0]

    def scalar(key):
        pattern = r'(?<![\w$])' + re.escape(key) + r':\s*("(?:\\.|[^"\\])*"|null|true|false|-?\d+(?![\w.]))'
        m = re.search(pattern, block)
        if m is None:
            raise DownloadError(f'Metadata field missing: {key}; website format changed')
        return json.loads(m.group(1))

    keys = ('id', 'teamAId', 'teamBId', 'submissionAId', 'submissionBId', 'mapId',
            'ranked', 'status', 'winner', 'seriesId', 'mapName', 'teamAName', 'teamBName')
    meta = {key: scalar(key) for key in keys}
    if meta['id'] != match_id or meta['status'] != 'completed':
        raise DownloadError('Wrong match ID or match has not completed')
    if meta['ranked'] and not meta['seriesId']:
        raise DownloadError('Ranked match has no series ID; cannot group data safely')
    meta.update(match_id=match_id,
                group_id=f"series:{meta['seriesId']}" if meta['seriesId'] else f'match:{match_id}',
                source_url=f'{ORIGIN}/visualiser?match={match_id}')
    when = re.search(r'\bcompletedAt:new Date\((\d+)\)', block)
    if when:
        meta['completed_utc'] = datetime.fromtimestamp(int(when.group(1))/1000, timezone.utc).isoformat()
    return meta


def download_one(client, match_id, out):
    target = out / f'match_{match_id}.replay'
    sidecar = target.with_suffix('.meta.json')
    if target.is_file() and sidecar.is_file():
        meta = json.loads(sidecar.read_text(encoding='utf-8'))
        if meta.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest():
            return meta, False
    page = client.get(f'{ORIGIN}/visualiser?match={match_id}').decode('utf-8')
    meta = match_metadata(page, match_id)
    raw = client.get(f'{ORIGIN}/api/matches/{match_id}/replay', 64*1024*1024)
    temporary = target.with_name(target.name + '.part')
    try:
        temporary.write_bytes(raw)
        replay = load_replay(temporary)
        if not replay['result']['terminated']:
            raise DownloadError('Replay is not finished')
        for _ in replay['events']:
            pass  # Validate all event records before accepting the download.
        meta.update(sha256=hashlib.sha256(raw).hexdigest(),
                    downloaded_utc=datetime.now(timezone.utc).isoformat(),
                    bot_A=replay['bot_A'], bot_B=replay['bot_B'], result=replay['result'])
        temporary.replace(target)
        json_write(sidecar, meta)
    finally:
        temporary.unlink(missing_ok=True)
    return meta, True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=Path('top_replays'))
    p.add_argument('--limit', type=int, default=10, help='Maximum links to take from the current Top Battles page')
    p.add_argument('--ids', nargs='+', help='Optional known match IDs from Watch replay links')
    args = p.parse_args()
    if not 1 <= args.limit <= 100:
        p.error('--limit must be between 1 and 100')
    args.out.mkdir(parents=True, exist_ok=True)
    client = PublicClient()
    try:
        if args.ids:
            ids = list(dict.fromkeys(valid_id(x) for x in args.ids))
        else:
            rows = top_rows(client.get(TOP_URL).decode('utf-8'))[:args.limit]
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            json_write(args.out / f'top_index_{stamp}.json',
                       {'source_url': TOP_URL, 'fetched_utc': stamp, 'matches': rows})
            ids = [row['match_id'] for row in rows]
        failures = 0
        for match_id in ids:
            try:
                meta, downloaded = download_one(client, match_id, args.out)
                status = 'Downloaded' if downloaded else 'Already saved'
                print(f"{status} {match_id}: {meta['teamAName']} vs {meta['teamBName']} / {meta['mapName']}", flush=True)
            except (DownloadError, ValueError) as error:
                print(f'Match {match_id}: {error}', flush=True)
                if isinstance(error, DownloadError) and error.status in (401, 403, 429):
                    raise  # Do not work around access denial or keep sending after a rate limit.
                failures += 1
        print(f'Done: {len(ids)-failures}/{len(ids)} available in {args.out}', flush=True)
        if failures:
            p.exit(1)
    except DownloadError as error:
        p.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
