"""Inspect the last decisions before own largest and final dragon deaths.

Alternative exits use only that decision's 7x7 view. They are immediate
possibilities, not proofs of survival against a reacting opponent.
"""
from collections import deque
import json
from pathlib import Path

from make_dataset import Board, DIRS, DELTAS
from replay_reader import load_replay

ROOT=Path(__file__).resolve().parent


def exits(obs):
    tiles=obs['tiles']; hx,hy=obs['position']; w,h=obs['map']
    view={((hx+dx)%w,(hy+dy)%h):tiles[(dy+3)*7+dx+3]
          for dy in range(-3,4) for dx in range(-3,4)}
    result={}
    for d,(dx,dy) in enumerate(DELTAS):
        edge=tiles[24][3+2*d]; q=((hx+dx)%w,(hy+dy)%h)
        if edge==1: result[DIRS[d]]='wall'; continue
        if edge==2: result[DIRS[d]]='portal: needs endpoint evaluation'; continue
        if view[q][2]: result[DIRS[d]]='occupied'; continue
        threats=[]
        for pos,tile in view.items():
            if tile[2] not in (4,5): continue
            for e,(ex,ey) in enumerate(DELTAS):
                if tile[3+2*e]==0 and ((pos[0]+ex)%w,(pos[1]+ey)%h)==q:
                    threats.append('enemy' if tile[2]==5 else 'ally')
        result[DIRS[d]]='open'+(' + pearl' if view[q][0] else '')+(
            ' + reachable by '+','.join(threats)+' head' if threats else ' (no visible one-step head threat)')
    return result


def main():
    output=[]
    for path in sorted((ROOT/'my_replays').glob('*.replay')):
        meta=json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
        side='A' if meta['teamAId']==128 else 'B'
        r=load_replay(path); b=Board(r['map']); deaths=[]
        for e in r['events']:
            if e['type']=='dragonDeath' and b.dragons[e['id']]['team']==side:
                deaths.append(dict(round=b.round,id=e['id'],length=len(b.dragons[e['id']]['body']),reason=e['reason']))
            b.apply(e)
        if not deaths: continue
        targets={d['id']:d for d in (max(deaths,key=lambda x:x['length']),deaths[-1])}
        history={i:deque(maxlen=3) for i in targets}
        r=load_replay(path); b=Board(r['map'])
        for e in r['events']:
            if e['type']=='dragonAction' and e['id'] in targets:
                obs=b.observation(e['id'])
                history[e['id']].append(dict(round=b.round,head=obs['position'],length=obs['length'],
                    unit_count=obs['unit_count'],action=e['action'],exits=exits(obs),observation=obs))
            b.apply(e)
        for ident,death in targets.items():
            output.append(dict(match=meta['match_id'],map=meta['mapName'],side=side,
                submission=meta['submission'+side+'Id'],death=death,decisions=list(history[ident])))
        print(f'Inspected {meta["match_id"]}',flush=True)
    out=ROOT/'coaching'; out.mkdir(exist_ok=True)
    (out/'decisive_positions.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Decisions before major own deaths','',
        'Open means no immediate wall/body collision in the recorded view; it does not guarantee a safe future. '
        'Head threats cover visible one-step ordinary moves, not sprint or unknown portal attacks. '
        'A death can happen after the actor moved, on another dragon turn. Rounds start at zero.','']
    for row in output:
        d=row['death']; lines += [f'## {row["match"]} / {row["map"]} / dragon {d["id"]}', '',
            f'Death R{d["round"]}: {d["reason"]}, length {d["length"]}, submission {row["submission"]}.','']
        for step in row['decisions']:
            lines.append(f'- R{step["round"]}, head {step["head"]}, length {step["length"]}, '
                f'{step["unit_count"]} allied units: `{json.dumps(step["action"])}`; exits: '+
                '; '.join(k+'='+v for k,v in step['exits'].items()))
        lines.append('')
    (out/'decisive_positions.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__': main()
