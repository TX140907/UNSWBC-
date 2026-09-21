"""Fetch own completed games with exact team/submission/map identities."""
import argparse
import hashlib
import json
from pathlib import Path
from download_battles import Client, api_key, json_write, save_replay, DownloadError
from analyze_replays import analyze, markdown

ROOT=Path(__file__).resolve().parent

def sync(client, out, team=128, submission=None, ids=None):
    out.mkdir(parents=True,exist_ok=True)
    if ids is None:
        recent=client.json('battles?limit=200')
        ids=[r['id'] for r in recent]
    todo=[]
    for ident in ids:
        detail=client.json(f'battles/{ident}')
        match=detail['match']
        side='A' if match['teamAId']==team else 'B' if match['teamBId']==team else None
        if side is None: raise DownloadError('Wrong own team')
        if submission is not None and match['submission'+side+'Id']!=submission: continue
        todo.extend(g['id'] for g in detail['games'] if g['status']=='completed')
    summaries=[]
    for ident in dict.fromkeys(todo):
        target=out/f'battle_{ident}.replay'; sidecar=target.with_suffix('.meta.json')
        if target.exists() and sidecar.exists():
            meta=json.loads(sidecar.read_text(encoding='utf-8'))
            if meta.get('validated') and meta['sha256']==hashlib.sha256(target.read_bytes()).hexdigest():
                summaries.append(analyze(target)); continue
        detail=client.json(f'battles/{ident}'); match=detail['match']
        side='A' if match['teamAId']==team else 'B' if match['teamBId']==team else None
        if side is None or match['status']!='completed': continue
        if submission is not None and match['submission'+side+'Id']!=submission: continue
        paths=save_replay(out,ident,client.get(f'battles/{ident}/replay'))
        if paths!=[target.name]: raise DownloadError('Expected one binary game replay')
        meta={k:match.get(k) for k in ('teamAId','teamBId','submissionAId','submissionBId','mapId','ranked','status','seriesId')}
        meta.update({k:detail[k] for k in ('mapName','teamAName','teamBName')})
        meta.update(match_id=ident,group_id=f'series:{match["seriesId"]}' if match['seriesId'] else f'match:{ident}',
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                    source_url=f'https://game.battlecode.au/visualiser?match={ident}')
        json_write(sidecar,meta)
        summary=analyze(target); summaries.append(summary)
        meta['validated']=True;json_write(sidecar,meta)
        json_write(out/f'battle_{ident}.detail.json',detail)
        print(f'{ident}: {detail["mapName"]} / own submission {match["submission"+side+"Id"]}',flush=True)
    json_write(out/'report.json',summaries)
    (out/'report.md').write_text(markdown(summaries),encoding='utf-8')
    return summaries

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--submission',type=int)
    p.add_argument('--ids',nargs='+',type=int)
    p.add_argument('--out',type=Path,default=ROOT/'loop_replays')
    a=p.parse_args();sync(Client(api_key()),a.out,submission=a.submission,ids=a.ids)
