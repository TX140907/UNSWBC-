"""Download recent own battles or explicit battle IDs through the official API.

GET requests only. Reads the Battlecode TEAM key from UNSWBC_API_KEY or a hidden
prompt. The key is never written to disk or forwarded to replay storage hosts.
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import getpass
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

BASE = 'https://game.battlecode.au/api/v1/'
MAX_DOWNLOAD = 64*1024*1024


def api_key(prompt=True):
    """Use the official server's toolkit credential without displaying it."""
    key = os.environ.get('UNSWBC_API_KEY') or os.environ.get('UNSWBC_KEY')
    if not key:
        home = Path(os.environ.get('USERPROFILE', str(Path.home())))
        try:
            key = json.loads((home/'.unswbc/keys.json').read_text()).get('https://game.battlecode.au')
        except (OSError, ValueError, AttributeError):
            pass
    if not key and prompt:
        key = getpass.getpass('Battlecode TEAM API key (hidden): ')
    return (key or '').strip()


class DownloadError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, key):
        self.key = key
        self.opener = urllib.request.build_opener(NoRedirect())
        self.last_request = 0.0

    def get(self, path):
        url = BASE+path.lstrip('/')
        auth = True
        retries = 0
        redirects = 0
        while True:
            time.sleep(max(0, self.last_request+0.65-time.monotonic()))
            self.last_request = time.monotonic()
            headers = {'User-Agent': 'unswbc-replay-dataset/1.0'}
            if auth:
                headers.update(Authorization='Bearer '+self.key, Origin='https://game.battlecode.au')
            request = urllib.request.Request(url, headers=headers, method='GET')
            try:
                with self.opener.open(request, timeout=30) as response:
                    body = response.read(MAX_DOWNLOAD+1)
                    encoding = response.headers.get('Content-Encoding', '').lower()
                    if len(body) > MAX_DOWNLOAD:
                        raise DownloadError('Download exceeds 64 MiB')
                    if encoding == 'gzip' or body.startswith(b'\x1f\x8b'):
                        with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
                            body = stream.read(MAX_DOWNLOAD+1)
                        if len(body) > MAX_DOWNLOAD:
                            raise DownloadError('Decoded download exceeds 64 MiB')
                    return body
            except urllib.error.HTTPError as error:
                code, response_headers = error.code, error.headers
                error.close()
                if code in (301, 302, 303, 307, 308):
                    if redirects >= 5 or not response_headers.get('Location'):
                        raise DownloadError('Invalid or excessive redirects') from None
                    target = urllib.parse.urljoin(url, response_headers['Location'])
                    parsed = urllib.parse.urlsplit(target)
                    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                        raise DownloadError('Invalid replay redirect URL') from None
                    url, auth = target, False  # Never forward the team key.
                    redirects += 1
                    continue
                if code in (429, 500, 502, 503, 504) and retries < 4:
                    delay = 2**(retries+1)
                    value = response_headers.get('Retry-After')
                    if value:
                        try:
                            delay = max(delay, float(value))
                        except ValueError:
                            try:
                                delay = max(delay, (parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
                            except (ValueError, TypeError):
                                pass
                    if delay > 300:
                        raise DownloadError('Server requests a long wait; run again later') from None
                    print(f'HTTP {code}: waiting {delay:.0f}s before retry')
                    time.sleep(delay)
                    retries += 1
                    continue
                hints = {401: 'Team API key was rejected', 403: 'Access denied to this battle or endpoint',
                         404: 'Battle/replay not available; check ID and whether the match finished',
                         409: 'Replay may not be ready', 429: 'Rate limit; try again later'}
                raise DownloadError(f'HTTP {code}: {hints.get(code, "request failed")}', code) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                # Do not echo signed URLs, request headers or credentials.
                raise DownloadError('Network error while downloading; try again later') from None

    def json(self, path):
        try:
            return json.loads(self.get(path))
        except (ValueError, UnicodeError):
            raise DownloadError('Expected API JSON but received another format') from None


def recent_rows(payload):
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        for key in ('battles', 'items', 'data'):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
        else:
            if isinstance(payload.get('data'), dict):
                return recent_rows(payload['data'])
            raise DownloadError('Unrecognized list response. Inspect recent.json and use --ids.')
    else:
        raise DownloadError('Unrecognized list response. Use --ids.')
    if not all(isinstance(r, dict) and ('id' in r or 'battleId' in r) for r in rows):
        raise DownloadError('Battle IDs not found. Inspect recent.json and use --ids.')
    return rows


def valid_id(value):
    text = str(value)
    if not text.isdecimal() or int(text) <= 0:
        raise DownloadError('Battle IDs must be positive integers')
    return int(text)


def atomic_write(path, data):
    temp = path.with_name(path.name+'.part')
    try:
        temp.write_bytes(data)
        # Windows sync/indexing software may briefly hold the destination open.
        for attempt in range(7):
            try:
                temp.replace(path)
                break
            except PermissionError:
                if attempt == 6:
                    raise
                time.sleep(0.05 * 2**attempt)
    finally:
        temp.unlink(missing_ok=True)


def json_write(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))


def save_replay(out, battle_id, raw):
    files = []
    if raw[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = [i for i in archive.infolist() if not i.is_dir() and i.filename.lower().endswith('.replay')]
            if not entries or len(entries) > 50 or sum(i.file_size for i in entries) > MAX_DOWNLOAD:
                raise DownloadError('Unexpected replay ZIP contents')
            # Generate our own filenames; never use untrusted ZIP paths.
            for index, entry in enumerate(entries):
                files.append((out/f'battle_{battle_id}_game_{index:02}.replay', archive.read(entry)))
    else:
        if not raw or raw.lstrip().startswith((b'<', b'{', b'[')):
            raise DownloadError('Endpoint did not return a binary replay')
        files.append((out/f'battle_{battle_id}.replay', raw))
    for path, content in files:
        atomic_write(path, content)
        json_write(path.with_suffix('.meta.json'), {'battle_id': battle_id,
                   'group_id': f'battle:{battle_id}', 'sha256': hashlib.sha256(content).hexdigest(),
                   'downloaded_utc': datetime.now(timezone.utc).isoformat()})
    return [p.name for p, _ in files]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument('--recent', type=int, help='Latest 1-200 OWN battles; no undocumented pagination')
    which.add_argument('--ids', nargs='+', help='Explicit accessible battle IDs')
    which.add_argument('--ids-file', type=Path, help='Text file, one battle ID per line')
    p.add_argument('--out', type=Path, default=Path('replays'))
    args = p.parse_args()
    if args.recent is not None and not 1 <= args.recent <= 200:
        p.error('--recent must be from 1 to 200')
    key = api_key()
    if not key.strip():
        p.error('No API key supplied')
    client = Client(key.strip())
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        if args.recent is not None:
            payload = client.json(f'battles?limit={args.recent}')
            json_write(args.out/'recent.json', payload)
            rows = recent_rows(payload)
            ids = [valid_id(r['id'] if 'id' in r else r['battleId']) for r in rows]
        elif args.ids_file:
            ids = [valid_id(line.strip()) for line in args.ids_file.read_text().splitlines() if line.strip()]
        else:
            ids = [valid_id(v) for v in args.ids]
        manifest = args.out/'downloads.json'
        done = json.loads(manifest.read_text()) if manifest.exists() else {}
        failed = 0
        for battle_id in dict.fromkeys(ids):
            old = done.get(str(battle_id), {})
            if old.get('files') and all((args.out/f).is_file() for f in old['files']):
                print(f'Skipped {battle_id}: already downloaded')
                continue
            try:
                detail = client.json(f'battles/{battle_id}')
                json_write(args.out/f'battle_{battle_id}.json', detail)
                raw = client.get(f'battles/{battle_id}/replay')
                paths = save_replay(args.out, battle_id, raw)
                done[str(battle_id)] = {'status': 'downloaded', 'files': paths}
                print(f'Downloaded {battle_id}: {len(paths)} replay file(s)')
            except (DownloadError, zipfile.BadZipFile) as error:
                if isinstance(error, DownloadError) and error.status == 401:
                    raise
                failed += 1
                print(f'Skipped {battle_id}: {error}')
            json_write(manifest, done)
        print(f'Done. Directory: {args.out}. Failed/unavailable this run: {failed}')
    except DownloadError as error:
        p.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
