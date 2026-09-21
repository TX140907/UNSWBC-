"""Compare supported action-class estimates for a saved decisive observation.

Example: python battlecode_data/score_position.py --match 5910 --dragon 81
Not a counterfactual simulation. Equal action classes receive equal estimates.
"""
import argparse
import json
from pathlib import Path
from coach_replays import observation_context,predict


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--match',type=int,required=True)
    p.add_argument('--dragon',type=int,required=True)
    args=p.parse_args()
    out=Path(__file__).resolve().parent/'coaching'
    positions=json.loads((out/'decisive_positions.json').read_text(encoding='utf-8'))
    row=next((r for r in positions if r['match']==args.match and r['death']['id']==args.dragon),None)
    if not row: p.error('No recorded decisive position for this match/dragon')
    model=json.loads((out/'action_model.json').read_text(encoding='utf-8'))
    for decision in row['decisions']:
        obs=decision['observation']
        choices=[dict(kind='move',steps=d) for d in 'NESW']
        if obs['length']>=4 and obs['unit_count']<obs['unit_limit']:
            choices += [dict(kind='split',child_length=n) for n in sorted({2,obs['length']-2})]
        scores=[]
        for action in choices:
            c=observation_context(obs,action)
            if c[-1].endswith(('-wall','-occupied')):
                scores.append(dict(action=action,rejected='immediate visible collision'))
                continue
            estimate=predict(model['buckets'],c)
            scores.append(dict(action=action,estimate=estimate,
                immediate_view=decision['exits'].get(action.get('steps',''),'split exit not evaluated'),
                note='Observed-class association only; tail/portal exit and future response not verified.'))
        print(json.dumps(dict(round=decision['round'],played=decision['action'],
            choices=scores),ensure_ascii=True,indent=2))


if __name__=='__main__': main()
