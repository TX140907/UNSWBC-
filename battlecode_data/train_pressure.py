"""Fit a bounded pressure-risk proposal from own replay outcomes, then gate locally.

This is parameter training, not reconstruction of opponents' source code. Replay
associations propose risk weights; real matches must validate the resulting bot.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from analyze_replays import analyze
from coach_replays import action_samples
from download_battles import json_write

ROOT=Path(__file__).resolve().parents[1]
START='// BEGIN TRAINED PRESSURE\n'
END='// END TRAINED PRESSURE\n'
OBSERVE=('        int enemyHeads=0,enemySegments=0;\n'
         '        for (auto const& tile:ct.get_tiles()) if (auto p=tile.get_dragon())\n'
         '            if (p->get_team()!=ct.get_team()) { ++enemySegments; enemyHeads+=p->is_head(); }\n'
         '        const int enemyPressure=(enemyHeads>=2 || enemySegments>=8)?8:0;\n')
RISK='                if (part->get_team()!=ct.get_team()) risk *= learnedPressure(w,h,ct.get_length(),enemyPressure);\n'


def strip_model(source):
    if START in source:
        a=source.index(START); b=source.index(END,a)+len(END)
        source=source[:a]+source[b:]
    source=source.replace(RISK,'').replace(OBSERVE,'')
    return source


def source_with_model(source, weights):
    source=strip_model(source)
    if not weights: return source
    # Local tiles only: >=8 enemy segments or >=2 enemy heads, encoded separately.
    code=START+'double learnedPressure(int w,int h,int length,int pressure) {\n'
    code+='    if(pressure<8) return 1.0;\n'
    for size,weight in sorted(weights.items()):
        size,category=size.split('/')
        w,h=map(int,size.split('x'))
        condition='length>=8' if category=='long' else 'length<8'
        code+=f'    if(w=={w} && h=={h} && {condition}) return {weight:.3f};\n'
    code+='    return 1.0;\n}\n'+END
    marker='\n        for (auto const& tile : ct.get_tiles()) if (auto part = tile.get_dragon()) {'
    if source.count(marker)!=1 or source.count('                danger[q] += risk;')!=1:
        raise ValueError('Training hook no longer matches source')
    source=source.replace(marker,'\n'+OBSERVE+marker[1:])
    source=source.replace('                danger[q] += risk;',
        RISK+'                danger[q] += risk;')
    return code+source


def fit(directory, out, team=128):
    cache=ROOT/'battlecode_data/training_loop/sample_cache';cache.mkdir(parents=True,exist_ok=True)
    samples=[]; seen=set(); provenance=[]
    for path in sorted(directory.glob('*.replay')):
        meta=json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
        if not meta.get('validated'): continue
        side='A' if meta['teamAId']==team else 'B' if meta['teamBId']==team else None
        if side is None: continue
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen: continue
        seen.add(digest)
        target=cache/f'{digest}-{side}.json'
        if target.exists(): data=json.loads(target.read_text())
        else:
            summary=analyze(path);summary['sha256']=digest
            # A crashing opponent is not a strategic win; discard the entire game.
            invalid=any(r['death_counts'].get('noValidAction',0) for r in summary['teams'].values())
            data=[] if invalid else [r for r in action_samples(path,summary,600) if r['team']==side]
            json_write(target,data)
        samples.extend(data)
        provenance.append(dict(match=meta['match_id'],group=meta['group_id'],sha256=digest,
            submission=meta['submission'+side+'Id']))
    groups=sorted({r['group'] for r in samples})
    split_path=cache/'group_split.json'
    assignments=json.loads(split_path.read_text()) if split_path.exists() else {}
    if not assignments and len(groups)>=3:
        ordered=sorted(groups,key=lambda g:hashlib.sha256(g.encode()).hexdigest())
        first_held=set(ordered[:max(1,len(groups)//5)])
        assignments={g:g in first_held for g in groups}
    for g in groups:
        assignments.setdefault(g,int(hashlib.sha256(g.encode()).hexdigest()[:8],16)%5==0)
    json_write(split_path,assignments)
    held={g for g in groups if assignments[g]}
    buckets=defaultdict(lambda: [[],[]])
    for r in samples:
        if r['action']['kind']!='move': continue
        if len(r['action']['steps'])!=1: continue
        key=(r['context'][0]+('/long' if r['length']>=8 else '/short'),r['group'] in held)
        buckets[key][r['context'][-2]=='many-enemies'].append(r)
    weights={}; evidence=[]
    for size in sorted({k[0] for k in buckets}):
        quiet,pressured=buckets[(size,False)]
        vquiet,vpressured=buckets[(size,True)]
        mean=lambda rows: sum(r['score'] for r in rows)/len(rows) if rows else None
        delta=mean(quiet)-mean(pressured) if quiet and pressured else None
        validation_delta=mean(vquiet)-mean(vpressured) if vquiet and vpressured else None
        enough=(min(len(quiet),len(pressured))>=30 and
                min(len({r['group'] for r in quiet}),len({r['group'] for r in pressured}))>=2)
        # Holdout is separate whole series. No holdout => abstain from new weights.
        accepted=enough and delta>1 and min(len(vquiet),len(vpressured))>=10 and validation_delta>0
        if accepted: weights[size]=round(1+min(.45,delta/40),3)
        evidence.append(dict(size=size,train_counts=[len(quiet),len(pressured)],
            validation_counts=[len(vquiet),len(vpressured)],delta=delta,
            validation_delta=validation_delta,proposed_weight=weights.get(size,1)))
    out.mkdir(parents=True,exist_ok=True)
    json_write(out/'fit.json',dict(weights=weights,evidence=evidence,matches=provenance,
        train_groups=sorted(set(groups)-held),holdout_groups=sorted(held),
        warning='Associations are not causal counterfactual estimates; candidate requires match gate.'))
    return weights


def build_candidate(bot, out, weights):
    out.mkdir(parents=True,exist_ok=True)
    for name in ('helper.hpp','bot.toml'): shutil.copy2(bot/name,out/name)
    (out/'main.cpp').write_text(source_with_model((bot/'main.cpp').read_text(),weights))
    subprocess.run(['g++','-std=c++20','-O2',str(out/'main.cpp'),'-o',str(out/'bot.exe')],check=True,cwd=ROOT)


if __name__=='__main__':
    out=ROOT/'battlecode_data/training_loop/round1'
    weights=fit(ROOT/'battlecode_data/loop_replays',out)
    build_candidate(ROOT/'Leviathan',out/'candidate',weights)
    print(json.dumps(weights))
