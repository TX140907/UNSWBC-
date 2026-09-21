# Kraken Counter Campaign

Objective: a real final 20/20 sweep against one frozen current Leviathan binary
on the ten repository maps, both A/B sides. This objective is not achieved yet.

## Current Campaign

The dimension-only campaign paused after cycle 1 at **13/20** (Queen of Spades B
was added). Its standalone champion and all evidence remain intact. Do not resume
that output against the now side-aware root sources.

The active campaign is `benchmark-results/kraken-side-campaign`. Its fresh full
baseline completed with **15 wins / 5 losses / 0 errors**, with policies selected using only map
dimensions and the observed A/B team letter. Two additional A-side hypotheses
were exported for 64x64 and 32x32; no old scores were imported. The frozen opponent
is copied byte-for-byte from the prior campaign. Baseline losses were Big Empty B,
Colosseum B, both Queen maps A, and Schooltime B.
Baseline artifacts: `cycle-0000-20260921T145155797544/baseline/run_20260922_005155_819725/`
inside the active campaign. This is a real combined-bot baseline, not the required
20/20 success verification.

Side-aware cycle 0 improved Schooltime B with `worker_continuation=10` while
retaining its `risk_percent=75`, bringing grouped training results to **16/20**.
Cycles 0 through 3 are complete; cycle 4 collected evidence and is paused for an
isolated terrain experiment. Remaining targets are Big Empty B, Colosseum B, and
both Queen maps A. Forty-seven unit tests passed, including deployment safeguards
and exhaustive three-game win/draw/loss checks of the rejection certificate. The 16/20 combined champion
has not yet undergone another full sweep; final success still requires 20/20.

```powershell
python battlecode_data/train_kraken.py --until-perfect --side-aware --publish --cache-dir benchmark-results/kraken-counter-campaign/cache --pages 1 --limit 30 --timeout 2400 --out benchmark-results/kraken-side-campaign
```

`seed_kraken_sides.py` records the historical source of each proposed override in
`benchmark-results/kraken-side-seed.meta.json`. Only fresh games count in this
new campaign. Tests cover A/B scheduling, side-specific history, seed validation,
and compiled C++ override/fallback selection.

The latest evidence pass contains 565 decisive unique public replays across eight
maps. Remove the campaign's `stop.request` before resuming the command above.

## Root Deployment

The trained header and exact champion executable were published to `Kraken/` on
2026-09-22. Previously the root header still contained defaults and its executable
was stale, so running the root folder did not run the reported trained champion.
Original files and the deployment audit are retained in
`benchmark-results/kraken-side-campaign/deployments/20260921T155811513724/`.
The actual folder-versus-folder workflow then won Default on both A and B, with
zero errors, in `benchmark-results/kraken-deployment-check/evaluation/`.
This two-game deployment check is not a full campaign verification.
Future accepted champions are published with backups when `--publish` is enabled.

## Recorded Results (2026-09-22)

- The latest completed evidence pass analyzed 288 decisive unique replays on
  eight named maps with no rejected files. Collection continues every cycle.
- Campaign cycle 0 completed with 12/20 grouped wins, up from the 3/20 baseline.
  Wins: Arena A/B, Colosseum A, Default Small A/B, Default B, Big Empty A,
  Help B, Queen of Spades But She Ages B, Schooltime A, Trophy A/B.
  This has not yet passed the required fresh combined-bot verification.
- Full baseline directory: `benchmark-results/kraken-counter-v2/`.
  Baseline now has all 20 games: 3 wins, 17 losses. Help B timed out at 600 seconds
  on the first attempt, then finished in 267.4 seconds when run alone; Kraken won.
- Arena: `worker_continuation=40` won both A and B and passed protocol/rescue
  checks. Reconfirmed against the exact campaign opponent in
  `benchmark-results/kraken-arena40-frozen-confirmation/experiment.json`.
- Default: `growth_round=350, stop_round=420` lost both sides. Rejected.
  Artifact: `benchmark-results/kraken-default-growth350-tested/experiment.json`.
- Default: `risk_percent=75` also lost both sides. Rejected.
  Artifact: `benchmark-results/kraken-default-risk75/experiment.json`.

Frozen opponent: `benchmark-results/kraken-counter-v2/Leviathan.exe`.
SHA-256: `730ae9718264a641062d580ee26147f8c4bdabdb78b022b8af00138edda83cb4`.
Do not replace this executable or change Leviathan to make the target easier.

## Previous Campaign

The composition below has already been created. It began with 5/20 grouped wins
and the first complete cycle increased that to 12/20. The
dimension-only trainer ran from `benchmark-results/kraken-counter-campaign`.
That campaign is now archived; do not resume it with the new root sources or
recreate it with the merge command. The exact historical commands
used to compose and start it were:

```powershell
python battlecode_data/merge_kraken_experiments.py --base benchmark-results/kraken-counter-v2/checkpoint.json --from-results benchmark-results/kraken-arena40-frozen-confirmation/experiment.json benchmark-results/kraken-default-growth350-tested/experiment.json benchmark-results/kraken-default-risk75/experiment.json --out benchmark-results/kraken-counter-campaign
python battlecode_data/train_kraken.py --until-perfect --pages 1 --limit 30 --timeout 2400 --out benchmark-results/kraken-counter-campaign
```

After cycle 0, the trainer was restarted with `--allow-trainer-update` to load
search-family rotation and independent Top/All crawl quotas. The update is audited
in the checkpoint; bot, map and opponent identities remain unchanged. The current
driver supports a graceful pause by creating `OUT/stop.request` (remove it before
resuming). The first restart used a verified process-tree stop only after cycle 0
was saved because the previously running driver did not yet support this signal.

Cycle 1's first 64x64 candidate (`split_length=8, risk_percent=75`) won Big Empty
A/B and Help A but lost Help B. It was rejected under map/side non-regression;
the champion remains 12/20. A transient Windows `PermissionError` on the final
CSV replacement stopped the runner after all four games had been saved. The
runner now retries that atomic replace up to eight times. Its persistence-only
hash update was explicitly audited, without changing engine arguments or scoring.
`recover_kraken_candidate.py` verified source/policy/map identities, frozen opponent,
all four replay outcomes and protocol checks before recording the rejected trial.
The resumed trainer skips this completed group and continues cycle 1.

The merged scores are per-group training evidence, not a final combined-bot
verification. The continuous runner only announces success after a fresh full
20-game sweep. Frozen executable hashes matter: the earlier isolated Arena
trainer compiled a separate PE binary, so use the exact-opponent confirmation
experiment for composition, not that older checkpoint.

## Experimental Performance Work

`benchmark-results/kraken-speed-experiment/source/` contains a separate candidate
with reusable flood-fill storage and compact reverse adjacency. It has NOT been
adopted into the source Kraken or any campaign score. Differential checks passed
90 flood cases, unsigned epoch wrap, nine searches, 30 observed portal states and
actions, and repeated observations. Its standalone bot passed 12 protocol cases.
One local microbenchmark measured observation processing at 0.264 vs 0.029 seconds
for 200 calls; this is not a measured whole-game speedup.

The root Kraken now exposes movement and reproduction parameters. The Python
trainer rotates parameter families, avoids repeated/default proposals, preserves
strict map/side non-regression, and drops large replay summaries before matches.
Runtime errors and timeouts do not count as losses. Recovery rechecks completed
replay winners and runs only missing sides, including correct B-side attribution.
