"""Immutable strategy snapshots and DIRECT matchup evidence, never transitive ranks."""
import hashlib
import json
import math
import re
from pathlib import Path
import shutil
from download_battles import json_write


def archive(root, source, label):
    root,source=Path(root),Path(source)
    files={p.name:p.read_bytes() for p in sorted(source.iterdir())
           if p.is_file() and p.suffix in ('.cpp','.hpp','.py','.toml')}
    if not {'main.cpp','main.py'} & files.keys(): raise ValueError('Missing source')
    digest=hashlib.sha256()
    for name,data in files.items():
        digest.update(name.encode()+b'\0'+data+b'\0')
    ident=digest.hexdigest()
    dest=root/'strategies'/ident
    if dest.exists():
        if any((dest/name).read_bytes()!=data for name,data in files.items()):
            raise ValueError('Archived strategy was modified')
    else:
        dest.mkdir(parents=True)
        for name,data in files.items(): (dest/name).write_bytes(data)
        json_write(dest/'identity.json',dict(id=ident,label=label))
    return ident


def select_counter(rows, *, map_name, phase, opponent_style, generic,
                   min_pairs=4, min_opponents=2):
    """Only use paired direct tests in the same observed context, both sides.

    Rows describe a completed match, with immutable own/opponent strategy IDs,
    map hash, engine ID, seed, side, and a style inferred from legal observations.
    Aggregate opponent names or an A>B>C chain are insufficient evidence.
    """
    points={'win':1.0,'draw':0.5,'loss':0.0}
    cells={}
    for row in rows:
        if (row['map']!=map_name or row['phase']!=phase or
            row['observed_style']!=opponent_style or not row.get('valid') or
            row.get('style_confidence',0)<0.75): continue
        key=(row['strategy'],row['opponent'],row['map_sha'],row['engine'],row['seed'],row['side'])
        if row['result'] not in points: continue
        if key in cells and cells[key]!=points[row['result']]:
            raise ValueError('Conflicting deterministic matchup observations')
        cells[key]=points[row['result']]
    base={k[1:]:v for k,v in cells.items() if k[0]==generic}
    winner=generic; best=0.0
    for strategy in sorted({k[0] for k in cells}-{generic}):
        candidate={k[1:]:v for k,v in cells.items() if k[0]==strategy}
        paired=set(base)&set(candidate)
        # Require complete A/B pairs for each opponent/map/engine/seed.
        paired={k for k in paired if (*k[:-1], 'B' if k[-1]=='A' else 'A') in paired}
        if len(paired)<min_pairs or len({k[0] for k in paired})<min_opponents: continue
        gain=sum(candidate[k]-base[k] for k in paired)/len(paired)
        if gain>best:
            best=gain;winner=strategy
    return winner


def matchup_graphs(rows):
    """One directed graph per exact map revision AND phase; no transitive closure.

    Whole-game outcomes may seed offline graphs but are not phase-labelled
    runtime counter evidence. Repeated deterministic fixtures count only once.
    """
    groups={};seen={}
    for row in rows:
        if not row.get('valid') or row['result'] not in ('win','loss','draw'):continue
        key=(row['map'],row['map_sha'],row['phase'])
        fixture=(key,row['strategy'],row['opponent'],row['engine'],row['seed'],row['side'])
        if fixture in seen:
            if seen[fixture]!=row['result']:raise ValueError('Conflicting graph fixture')
            continue
        seen[fixture]=row['result']
        graph=groups.setdefault(key,{})
        a,b=row['strategy'],row['opponent']
        score={'win':1.0,'loss':0.0,'draw':0.5}[row['result']]
        pair=graph.setdefault((a,b),[]);pair.append((score,row['side']))
    result=[]
    for (name,digest,phase),pairs in sorted(groups.items()):
        edges=[]
        for (a,b),games in sorted(pairs.items()):
            score=sum(g[0] for g in games)/len(games)
            winner,loser=(a,b) if score>0.5 else (b,a)
            edges.append(dict(source=winner,target=loser,score=max(score,1-score),weight=max(score,1-score),
                games=len(games),both_sides={g[1] for g in games}=={'A','B'},
                relation='tie' if score==0.5 else 'observed_advantage',
                runtime_enabled=False,
                warning='Descriptive direct matchup; not a proven counter or a phase-conditioned policy.'))
        result.append(dict(map=name,map_sha=digest,phase=phase,
            nodes=sorted({x for pair in pairs for x in pair}),edges=edges))
    return result


def strongest_counter(graphs, *, map_name, map_sha, phase, opponent_strategy,
                      generic, available, confidence=1.0, current=None, runtime_only=True):
    """Argmax incoming edge into the confirmed enemy, in exactly one map graph.

    Weight is direct matchup points/game: WIN=1, DRAW=.5, LOSS=0.
    available contains only strategies the caller can actually execute.
    Runtime ignores unvalidated edges; runtime_only=False is offline analysis.
    """
    if not opponent_strategy or not math.isfinite(confidence) or confidence<0.75:
        return generic
    matching=[g for g in graphs if (g['map'],g['map_sha'],g['phase'])==(map_name,map_sha,phase)]
    if len(matching)>1: raise ValueError('Ambiguous map graph')
    if not matching:return generic
    weights={}
    for edge in matching[0]['edges']:
        if (edge['target']!=opponent_strategy or edge['source'] not in available or
            edge.get('relation')!='observed_advantage' or
            (runtime_only and not edge.get('runtime_enabled',False))):continue
        weight=edge.get('weight',edge.get('score'))
        if not isinstance(weight,(int,float)) or not math.isfinite(weight) or not 0.5<weight<=1:continue
        weights[edge['source']]=max(weights.get(edge['source'],0),weight)
    if not weights:return generic
    maximum=max(weights.values())
    tied=sorted(k for k,v in weights.items() if v==maximum)
    if current in tied:return current
    if generic in tied:return generic
    return tied[0]


class CounterSelector:
    """Call on EVERY refreshed opponent estimate, including lost confidence.

    Recompute instead of caching a best strategy across opponents or maps.
    Observation smoothing belongs to the detector, not to graph traversal.
    """
    def __init__(self,generic,available):
        self.generic=generic;self.available=set(available);self.current=generic

    def update(self,graphs,**observation):
        self.current=strongest_counter(graphs,generic=self.generic,available=self.available,
                                       current=self.current,**observation)
        return self.current


def write_graphs(library, graphs):
    library=Path(library)
    (library/'counter_graphs').mkdir(parents=True,exist_ok=True)
    json_write(library/'map_graphs.json',graphs)
    index=[]
    for graph in graphs:
        context=json.dumps([graph['map'],graph['map_sha'],graph['phase']]).encode()
        digest=hashlib.sha256(context).hexdigest()[:16]
        slug=re.sub(r'[^A-Za-z0-9_-]','_',graph['map'])
        relative=Path('counter_graphs')/(slug+'-'+digest+'.json')
        json_write(library/relative,graph)
        index.append(dict(map=graph['map'],map_sha=graph['map_sha'],phase=graph['phase'],file=relative.as_posix()))
    json_write(library/'counter_graphs/index.json',index)


def preserve_campaign(campaign, library):
    campaign,library=Path(campaign),Path(library)
    entries=[]
    for folder in [campaign/'initial',*sorted(campaign.glob('round*/*'))]:
        if (folder/'main.cpp').exists():
            entries.append(dict(path=str(folder),strategy=archive(library,folder,str(folder))))
    json_write(library/('inventory-'+campaign.name+'.json'),dict(strategies=entries,
        note='Append-only strategy snapshots; no opponent style is assigned from team name or final unit count.'))
    return entries


def import_campaign_games(campaign, library):
    campaign,library=Path(campaign),Path(library)
    preserve_campaign(campaign,library)
    data=library/'legacy_matchups.json'
    rows=json.loads(data.read_text()) if data.exists() else []
    known={(r['source'],r['map'],r['side']) for r in rows}
    for stage,folder in [('before','baseline'),('after','proposal'),('merged','candidate')]:
        for path in sorted(campaign.glob(f'round*/{stage}/*/results.json')):
            meta=json.loads((path.parent/'metadata.json').read_text())
            own_source=path.parents[2]/folder
            own=archive(library,own_source,str(own_source))
            enemy=archive(library,campaign/'opponents'/path.parent.name,path.parent.name)
            for game in json.loads(path.read_text()):
                key=(str(path),game['map'],game['side'])
                if key in known:continue
                known.add(key)
                rows.append(dict(strategy=own,opponent=enemy,map=game['map'],
                    map_sha=meta['maps'][game['map']+'.map'],engine=meta['toolkit'],
                    seed=None,side=game['side'],phase='whole-game',observed_style='unknown',
                    style_confidence=0,result=game['result'],source=str(path),
                    valid=game['result']!='error' and not game['timed_out'] and game['returncode']==0))
    json_write(data,rows)
    write_graphs(library,matchup_graphs(rows))
    return rows


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--library',type=Path,default=Path(__file__).resolve().parent/'strategy_library')
    args=parser.parse_args()
    print(f'Imported {len(import_campaign_games(args.campaign,args.library))} direct match observations; no upload.')
