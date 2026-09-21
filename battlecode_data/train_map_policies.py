"""Replay-guided, map-local proposals and paired selection. Never uploads itself."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from map_scorecard import write_scorecard, scorecard
from download_battles import json_write

ROOT = Path(__file__).resolve().parents[1]
OPPONENTS = ('Kraken', 'mybot', 'NamBot')
PLANS = {'arena':'Arena', 'Colosseum':'Colosseum', 'default_small':'DefaultSmall',
         'default':'Default', 'trophy':'Trophy', 'schooltime':'Schooltime'}
START = '        // BEGIN MAP TRAINING\n'
END = '        // END MAP TRAINING\n'


def policies(source):
    if START not in source: return {}
    block = source.split(START,1)[1].split(END,1)[0]
    return dict(re.findall(r'case MapPlan::(\w+): (.*?) break;', block))


def with_policies(source, values):
    if START in source:
        a=source.index(START); b=source.index(END,a)+len(END)
        source=source[:a]+source[b:]
    marker='        return p;\n    }\n    int childRoom() const'
    if source.count(marker)!=1: raise ValueError('Map policy hook changed')
    block=START+'        switch (mapPlan()) {\n'
    block+=''.join(f'        case MapPlan::{name}: {body} break;\n' for name,body in sorted(values.items()))
    block+='        default: break;\n        }\n'+END
    return source.replace(marker,block+marker) if values else source


def choose_maps(before, after, maps, opponents=OPPONENTS):
    card=scorecard(before,after,maps,opponents)
    if not card['complete']: raise ValueError('Missing paired map coverage')
    return [r['map'] for r in card['maps'] if r['after']>r['before']]


def propose(source, reports, number):
    losses={}; seen=set()
    for path in reports:
        for game in json.loads(path.read_text(encoding='utf-8')):
            ident=game.get('match_id')
            if ident in seen: continue
            seen.add(ident)
            if any(t.get('death_counts',{}).get('noValidAction',0) for t in game['teams'].values()):
                continue
            side=next((s for s,t in game['teams'].items() if t.get('name')=='An IQ too high?'),None)
            if side and game['result']['winner'] not in (side,None):
                key=game['map_name'].lower().replace(' ','_')
                losses.setdefault(key,[]).append(dict(id=ident,reason=game['result']['end_reason']))
    values=policies(source); proposed={}
    # Explicit, bounded hypotheses. The replay is evidence of failure, not proof
    # these unplayed alternatives will succeed; only paired games select them.
    for name,plan in PLANS.items():
        evidence=losses.get(name.lower(),[])
        if not evidence: continue
        if plan in ('Trophy','Default'):
            body=(f'p.expand=true; p.cautiousChild=true; p.splitLength={6+2*(number-1)}; '
                  f'p.target={16+8*(number-1)}; p.reserve=8; p.stop=260;')
        else:
            body=f'p.continuation={0.2+0.15*number:.2f}; p.reserve={6+2*number};'
        values[plan]=body; proposed[name]=dict(plan=plan,body=body,evidence=evidence)
    return values, proposed


def build(folder, source, base):
    folder.mkdir(parents=True,exist_ok=True)
    if ((folder/'bot.exe').exists() and (folder/'main.cpp').read_text(encoding='utf-8')==source and
            all((folder/name).read_bytes()==(base/name).read_bytes() for name in ('helper.hpp','bot.toml'))):
        return
    (folder/'main.cpp').write_text(source,encoding='utf-8')
    for name in ('helper.hpp','bot.toml'): shutil.copy2(base/name,folder/name)
    subprocess.run(['g++','-std=c++20','-O2',str(folder/'main.cpp'),'-o',str(folder/'bot.exe')],check=True)


def matrix(bot, out, campaign):
    from learning_loop import benchmark
    print(f'Map matrix: {out}', flush=True)
    maps=[p.stem for p in sorted((ROOT/'maps').glob('*.map'))]
    def job(name):
        frozen=campaign/'opponents'/name
        if not frozen.exists():
            frozen.mkdir(parents=True)
            for path in (ROOT/name).iterdir():
                if path.suffix in ('.cpp','.hpp','.py','.toml'): shutil.copy2(path,frozen/path.name)
        enemy=frozen
        if (frozen/'main.cpp').exists():
            enemy=frozen/'bot.exe'
            if not enemy.exists():
                subprocess.run(['g++','-std=c++20','-O2',str(frozen/'main.cpp'),'-o',str(enemy)],check=True)
        rows=benchmark(bot,out/name,maps,enemy)
        return {(name,*k):v for k,v in rows.items()}
    result={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for rows in pool.map(job,OPPONENTS): result.update(rows)
    return result,maps


def train_round(base, out, campaign, number):
    source=(base/'main.cpp').read_text(encoding='utf-8')
    old=policies(source)
    reports=list((ROOT/'battlecode_data/training_loop/campaign').glob('round*/replays/report.json'))
    reports+=list(campaign.glob('round*/replays/report.json'))
    latest=ROOT/'battlecode_data/loop_replays/report.json'
    if latest.exists():
        evidence=out/'input_report.json'
        if not evidence.exists(): shutil.copy2(latest,evidence)
        reports.append(evidence)
    values,proposed=propose(source,reports,number)
    json_write(out/'fit.json',dict(proposals=proposed,method='Map-local policy hypotheses from own losses',
        abstained=['Big Empty/help: ambiguous early observations','Queen variants: shared observable identity']))
    baseline=out/'baseline'; build(baseline,source,base)
    candidate=out/'proposal'; build(candidate,with_policies(source,values),base)
    before,maps=matrix(baseline/'bot.exe',out/'before',campaign)
    after,_=matrix(candidate/'bot.exe',out/'after',campaign)
    write_scorecard(out,before,after,maps,OPPONENTS)
    selected=choose_maps(before,after,maps)
    print(f'Round {number}: maps with higher new score: {selected}', flush=True)
    merged=dict(old)
    for name in selected:
        if name in proposed: merged[PLANS[name]]=values[PLANS[name]]
    accepted=out/'candidate'; build(accepted,with_policies(source,merged),base)
    changed=(accepted/'main.cpp').read_text(encoding='utf-8')!=source
    if changed:
        final,_=matrix(accepted/'bot.exe',out/'merged',campaign)
        card=write_scorecard(out/'merged',before,final,maps,OPPONENTS)
        passed=all(r['after']>=r['before'] for r in card['maps']) and any(r['after']>r['before'] for r in card['maps'])
    else: passed=False
    json_write(out/'selection.json',dict(selected_maps=selected,passed=passed,
        rule='Strictly higher map score wins; ties keep old. Retest merged bot on every map.'))
    return passed,maps,proposed
