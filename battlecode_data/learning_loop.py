"""Three bounded train/test/challenge/collect rounds, total at most 20 games.

Uploads only a candidate passing local strategy/protocol and match regression
checks. Server builds activate automatically. Rejected proposals keep the current
bot. Whole-series holdout and replay associations do not prove general strength.
"""
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

from download_battles import Client, api_key, json_write, DownloadError
from challenge_cycle import (locked, load_state, prepare, reserve, post_battle,
                              UnknownPost, refresh, export_ids)
from sync_training_battles import sync
from train_pressure import fit, build_candidate
from analyze_replays import markdown
from map_scorecard import write_scorecard

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'battlecode_data/training_loop/campaign'
DATA=ROOT/'battlecode_data/loop_replays'
LEDGER=ROOT/'battlecode_data/experiments/128'
MAP_TRAINING=False


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def active(client):
    matches=[s for s in client.json('submissions') if s['status']=='active']
    if len(matches)!=1: raise DownloadError('Expected one active submission')
    return matches[0]['id']


def verify_source(client, ident, source):
    raw=client.get(f'submissions/{ident}/download')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for name in ('main.cpp','helper.hpp','bot.toml'):
            if z.read(name)!=(source/name).read_bytes():
                raise DownloadError('Active source differs from local bot; stop before training/challenging')


def checked(command, log):
    with log.open('w',encoding='utf-8') as f:
        subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)


def benchmark(bot, out, maps, opponent=None):
    opponent = opponent or ROOT/'tests/kraken-map-baseline.exe'
    expected={(name,s) for name in maps for s in 'AB'}
    if not (out/'results.json').exists() or len(json.loads((out/'results.json').read_text()))<len(expected):
        command=[sys.executable,'tests/benchmark.py','--bot',str(bot.relative_to(ROOT)),
                 '--opponent',str(opponent.relative_to(ROOT)),'--timeout','900','--output',str(out),
                 '--resume','--maps',*maps]
        subprocess.run(command,cwd=ROOT,check=True)
    rows=json.loads((out/'results.json').read_text())
    meta=json.loads((out/'metadata.json').read_text())
    if meta['opponent'] != str(opponent.relative_to(ROOT)):
        raise ValueError('Benchmark opponent identity changed')
    if meta['bot_files']!={str(bot.relative_to(ROOT)):sha(bot)}:
        raise ValueError('Benchmark source/executable changed')
    if any(sha(ROOT/name)!=digest for name,digest in meta['opponent_files'].items()):
        raise ValueError('Benchmark opponent changed')
    if any(sha(ROOT/'maps'/name)!=digest for name,digest in meta['maps'].items()):
        raise ValueError('Benchmark maps changed')
    keys=[(r['map'],r['side']) for r in rows]
    if len(keys)!=len(expected) or set(keys)!=expected or any(
            r['result']=='error' or r['timed_out'] or r['returncode'] for r in rows):
        raise ValueError('Incomplete or invalid local benchmark')
    return {(r['map'],r['side']):r['result'] for r in rows}


def gate(before, after):
    rank={'loss':0,'draw':1,'win':2}
    if not before or set(before)!=set(after): return False
    if any(v not in rank for v in (*before.values(), *after.values())): return False
    # Equal results cannot justify automatically replacing the active bot.
    return (all(rank[after[k]]>=rank[v] for k,v in before.items()) and
            any(rank[after[k]]>rank[v] for k,v in before.items()))


def full_local_gate(base, candidate, out):
    maps = [p.stem for p in sorted((ROOT/'maps').glob('*.map'))]
    if not maps: raise ValueError('No maps for local gate')
    before, after = {}, {}
    for name in ('Kraken', 'mybot', 'NamBot'):
        frozen = out/'opponents'/name
        if not frozen.exists():
            frozen.mkdir(parents=True)
            for path in (ROOT/name).iterdir():
                if path.suffix in ('.cpp', '.hpp', '.py', '.toml'):
                    shutil.copy2(path, frozen/path.name)
        opponent = frozen
        if (frozen/'main.cpp').exists():
            opponent = frozen/'bot.exe'
            if not opponent.exists():
                checked(['g++','-std=c++20','-O2',str(frozen/'main.cpp'),'-o',str(opponent)],
                        frozen/'build.log')
        for bot, label, target in ((base,'before',before),(candidate,'after',after)):
            result = benchmark(bot, out/'full-gate'/name/label, maps, opponent)
            target.update({(name,*key):value for key,value in result.items()})
            write_scorecard(out/'full-gate',before,after,maps,('Kraken','mybot','NamBot'))
    return gate(before, after), maps


def deploy(client, folder, label, record, save):
    # Persist a unique upload name BEFORE upload. On restart reconcile by name,
    # never blindly repeat a possibly successful upload.
    matches=[s for s in client.json('submissions') if s['name']==label]
    if len(matches)>1: raise DownloadError('Ambiguous upload name')
    if not matches:
        if record.get('upload_started'):
            raise DownloadError('Upload outcome unresolved; inspect server before retrying')
        record['upload_started']=True;save()
        checked(['unswbc','submit',str(folder),'-n',label,'-d',
                 'Replay-trained pressure risk; local regression gate passed'],folder.parent/'upload.log')
        matches=[s for s in client.json('submissions') if s['name']==label]
    if len(matches)!=1: raise DownloadError('Could not resolve submitted version')
    ident=matches[0]['id'];record['submission']=ident;save()
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        versions=client.json('submissions')
        version=next(s for s in versions if s['id']==ident)
        status=version['status']
        if status=='active':
            verify_source(client,ident,folder)
            return ident
        if status not in ('processing','queued','building'):
            raise DownloadError(f'Build not active: submission {ident}, status {status}; stop')
        print(f'Building submission {ident}...',flush=True);time.sleep(15)
    raise DownloadError('Build wait expired; resume later, no new upload')


def report(state):
    totals={k:sum(r.get('results',{}).get(k,0) for r in state['rounds']) for k in ('win','loss','draw')}
    sent=sum(len(r.get('battle_ids',[])) for r in state['rounds'])
    lines=['# Bounded Leviathan learning loop','',
           'Budget: 3 rounds, 20 total unranked games (7 / 7 / 6), rank radius 12.',
           f'Sent: {sent}/20 games. Completed results: {totals}.',
           ('Map-local policy proposals; select strictly higher scores separately per map and retest the merged bot. '
            if state.get('map_training') else 'Historical pressure-risk parameter training. ')+
           'Full validation uses all maps and both sides against three frozen local opponents; historical rounds used the narrower gate. '
           'Each round faces different opponents/maps; online win rates are not a paired before/after test.', '',
           '| Round | State | Submission | Local decision | Online W/L/D | Battle IDs |',
           '|---|---|---|---|---|---|']
    for r in state['rounds']:
        lines.append(f'| [{r["number"]}](round{r["number"]}/fit.json) | {r["phase"]} | {r.get("submission", "-")} | '
                     f'{r.get("decision", "-")} | {r.get("results", "-")} | {r.get("battle_ids", [])} |')
    lines+=['','## Replay reports','']
    for r in state['rounds']:
        if r['phase']=='done':
            lines.append(f'- [Round {r["number"]}: results and replays](round{r["number"]}/replays/report.md); '
                         f'learned proposal: `{r.get("weights", {})}`.')
    lines+=['','The last round\'s replays are retained for the next training campaign; this campaign stops after three fits.']
    (CAMPAIGN/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def run(client):
    CAMPAIGN.mkdir(parents=True,exist_ok=True)
    if (CAMPAIGN/'HOLD.json').exists():
        raise DownloadError('Campaign paused for map-specific counter-graph redesign; see HOLD.json. No upload or challenge sent.')
    manifest=CAMPAIGN/'state.json'
    if manifest.exists(): state=json.loads(manifest.read_text())
    else:
        current=active(client);verify_source(client,current,ROOT/'Leviathan')
        state=dict(initial_submission=current,map_training=MAP_TRAINING,rounds=[dict(number=i+1,budget=n,phase='new',battle_ids=[])
                                                      for i,n in enumerate((7,7,6))])
        json_write(manifest,state)
    def save(): json_write(manifest,state);report(state)
    if not state.get('initial_synced'):
        sync(client,DATA,submission=state['initial_submission'])
        state['initial_synced']=True;save()
    ledger=load_state(LEDGER,128)
    for row in state['rounds']:
        if row['phase']=='done': continue
        out=CAMPAIGN/f'round{row["number"]}';out.mkdir(exist_ok=True)
        if row['phase']=='new' and state.get('map_training'):
            from train_map_policies import train_round
            current=active(client);verify_source(client,current,ROOT/'Leviathan')
            row['previous_submission']=current
            passed,maps,proposals=train_round(ROOT/'Leviathan',out,CAMPAIGN,row['number'])
            candidate=out/'candidate'
            strategy=(ROOT/'tests/strategy.cpp').read_text().replace('../Leviathan/main.cpp','candidate/main.cpp')
            (out/'strategy.cpp').write_text(strategy)
            checked(['g++','-std=c++20','-O2',str(out/'strategy.cpp'),'-o',str(out/'strategy.exe')],out/'build-strategy.log')
            checked([str(out/'strategy.exe')],out/'strategy.log')
            checked([sys.executable,'tests/protocol_smoke.py',str(candidate/'bot.exe')],out/'protocol.log')
            row.update(local_maps=maps,weights=proposals,gate_version=3,
                       decision='selected per-map improvements' if passed else 'kept old policies: no validated improvement',
                       submission=current,phase='deploy' if passed else 'ready')
            save()
        if row['phase']=='new':
            current=active(client);verify_source(client,current,ROOT/'Leviathan')
            row['previous_submission']=current
            print(f'Round {row["number"]}: fit own replay data',flush=True)
            weights=fit(DATA,out)
            build_candidate(ROOT/'Leviathan',out/'candidate',weights)
            row['weights']=weights;row['phase']='fitted';save()
        if row['phase']=='fitted':
            candidate=out/'candidate'
            if (candidate/'main.cpp').read_text()==(ROOT/'Leviathan/main.cpp').read_text():
                row['decision']='unchanged: insufficient evidence or same weights'
                row['submission']=row['previous_submission'];row['phase']='ready';save()
            else:
                print(f'Round {row["number"]}: local gate',flush=True)
                strategy=(ROOT/'tests/strategy.cpp').read_text().replace('../Leviathan/main.cpp','candidate/main.cpp')
                (out/'strategy.cpp').write_text(strategy)
                checked(['g++','-std=c++20','-O2',str(out/'strategy.cpp'),'-o',str(out/'strategy.exe')],out/'build-strategy.log')
                checked([str(out/'strategy.exe')],out/'strategy.log')
                checked([sys.executable,'tests/protocol_smoke.py',str(candidate/'bot.exe')],out/'protocol.log')
                base=out/'baseline';base.mkdir(exist_ok=True)
                for name in ('main.cpp','helper.hpp','bot.toml'): shutil.copy2(ROOT/'Leviathan'/name,base/name)
                checked(['g++','-std=c++20','-O2',str(base/'main.cpp'),'-o',str(base/'bot.exe')],out/'build-baseline.log')
                passed,maps=full_local_gate(base/'bot.exe',candidate/'bot.exe',out)
                row['local_maps']=maps;save()
                row['gate_version']=2
                row['decision']='passed full local gate' if passed else 'rejected: regression or no improvement'
                row['phase']='deploy' if passed else 'ready'
                row['submission']=row['previous_submission'];save()
        if row['phase']=='deploy':
            if (CAMPAIGN/'HOLD.json').exists(): raise DownloadError('Campaign hold prevents upload')
            if row.get('gate_version') != (3 if state.get('map_training') else 2):
                raise DownloadError('Old narrow gate cannot authorize upload; rerun full local validation')
            label=f'Leviathan-{CAMPAIGN.name}-{state["initial_submission"]}-r{row["number"]}'
            row['submission']=deploy(client,out/'candidate',label,row,save)
            shutil.copy2(out/'candidate/main.cpp',ROOT/'Leviathan/main.cpp')
            shutil.copy2(out/'candidate/bot.exe',ROOT/'Leviathan/Leviathan.exe')
            row['phase']='ready';save()
        if row['phase']=='ready':
            if active(client)!=row['submission']: raise DownloadError('Active bot changed outside loop')
            verify_source(client,row['submission'],ROOT/'Leviathan')
            refresh(client,ledger,LEDGER)
            plan=prepare(client,ledger,12,row['budget'])
            row['targets']=plan['targets'];row['phase']='challenging';save()
        if row['phase']=='challenging':
            if (CAMPAIGN/'HOLD.json').exists(): raise DownloadError('Campaign hold prevents new challenges')
            # Campaign+round marker reconciles crash after POST state was saved.
            marker=(f'{CAMPAIGN.name}:' if state.get('map_training') else '')+f'{state["initial_submission"]}:{row["number"]}'
            for target in row['targets']:
                old=next((a for a in reversed(ledger['attempts']) if a.get('campaign')==marker and a['team_id']==target['team_id']),None)
                if old and old['status']=='rejected' and old.get('http_status')==429:
                    remaining=old.get('retry_at',0)-time.time()
                    if remaining>0:
                        error=DownloadError('Waiting for server rate limit',429)
                        error.retry_after=remaining
                        raise error
                    old=None  # confirmed rejection: safe to try once again after cooldown
                if old:
                    if old['status'] in ('uncertain','submitting','rejected'):
                        raise DownloadError('Unresolved/rejected challenge; stopped without retry')
                    continue
                if active(client)!=row['submission']: raise DownloadError('Active version changed')
                entry=reserve(ledger,target,time.time());entry['campaign']=marker
                json_write(LEDGER/'state.json',ledger)
                try:
                    entry['ids']=post_battle(client,target);entry['status']='submitted'
                except UnknownPost:
                    entry['status']='uncertain';raise
                except DownloadError as error:
                    entry['status']='rejected';entry['http_status']=error.status
                    if error.status==429:
                        entry['retry_at']=time.time()+getattr(error,'retry_after',60)
                    raise
                finally:
                    json_write(LEDGER/'state.json',ledger);export_ids(ledger,LEDGER)
                print(f'Round {row["number"]}: challenged team {target["team_id"]}, game {entry["ids"]}',flush=True)
            row['battle_ids']=[i for a in ledger['attempts'] if a.get('campaign')==marker for i in a['ids']]
            if not row['battle_ids']: raise DownloadError('No eligible opponents now; resume later')
            row['phase']='waiting';save()
        if row['phase']=='waiting':
            deadline=time.monotonic()+1800
            while time.monotonic()<deadline:
                done=True
                for ident in row['battle_ids']:
                    d=client.json(f'battles/{ident}')
                    m=d['match'];side='A' if m['teamAId']==128 else 'B'
                    if m['submission'+side+'Id']!=row['submission']:
                        raise DownloadError('Game used a different submission; do not train on mislabeled experiment')
                    if m['status']=='failed':
                        json_write(out/f'failed-{ident}.json',d)
                        raise DownloadError('Server game failed; stopped for log review')
                    done=done and m['status']=='completed'
                if done: break
                print(f'Round {row["number"]}: waiting for {len(row["battle_ids"])} games',flush=True)
                time.sleep(20)
            else: raise DownloadError('Queue wait limit reached; resume later with same state')
            summaries=sync(client,DATA,submission=row['submission'],ids=row['battle_ids'])
            archive=out/'replays';archive.mkdir(exist_ok=True)
            for summary in summaries:
                src=DATA/summary['file']
                for path in (src,src.with_suffix('.meta.json'),src.with_suffix('.detail.json')):
                    if path.exists(): shutil.copy2(path,archive/path.name)
            json_write(archive/'report.json',summaries)
            (archive/'report.md').write_text(markdown(summaries),encoding='utf-8')
            results={'win':0,'loss':0,'draw':0}
            for s in summaries:
                meta=json.loads((out/'replays'/s['file']).with_suffix('.meta.json').read_text())
                side='A' if meta['teamAId']==128 else 'B'
                results['draw' if s['result']['winner'] is None else 'win' if s['result']['winner']==side else 'loss']+=1
            row['results']=results;row['phase']='done';save()
            print(f'Round {row["number"]}: {results}',flush=True)
    report(state)
    print('Campaign complete; budget exhausted, no further challenges.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='Run/resume the authorized 3-round, 20-game campaign')
    parser.add_argument('--map-campaign',help='New/resumable map-local campaign directory name')
    args=parser.parse_args()
    if not args.run: parser.print_help();raise SystemExit(0)
    if args.map_campaign:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',args.map_campaign): parser.error('Invalid campaign name')
        if args.map_campaign=='campaign': parser.error('Preserve historical campaign')
        CAMPAIGN=ROOT/'battlecode_data/training_loop'/args.map_campaign
        MAP_TRAINING=True
    client=Client(api_key())
    waited=0
    while True:
        try:
            with locked(LEDGER): run(client)
            break
        except DownloadError as error:
            if error.status!=429 or waited>=3600:
                raise
            delay=min(60,getattr(error,'retry_after',60))
            print(f'Rate limited; waiting {delay:.0f}s, accepted games are not retried.',flush=True)
            time.sleep(delay);waited+=delay
