# Automated Kraken training

From the repository root (Python standard library, `g++`, and `unswbc` required):

```powershell
python battlecode_data/train_kraken.py --cycles 10 --pages 5 --limit 100
```

For the continuous counter-training objective (all ten maps, both starting sides):

```powershell
python battlecode_data/train_kraken.py --until-perfect --pages 3 --limit 100 --timeout 600 --out benchmark-results/kraken-counter-v2
```

This continues until the accumulated champion wins all 20 map/side pairs and a
fresh full 20-game verification also wins every game. It can take a long time;
there is no guarantee the current search space contains such a bot. Ctrl+C retains
the checkpoint. Failed proposals are not repeated; successful map groups are
skipped until the final combined-bot verification. Run only one trainer per output.
The current search also covers worker continuation, head-danger weight, pearl
reward, search depth, small-map army size/split length, and open-map expansion.

Each cycle downloads completed public games from Top Battles and All Battles,
checks replay checksums and final standings, deduplicates match IDs/content,
and compares winners with their losers separately for each map. Series receive
equal weight so one long series does not dominate the strategy proposal.
Corrupt files are recorded in `evidence.json` and excluded.

Each cycle uses observed winning split lengths and population differences on
large maps where at least two independent series are available. When this leaves
the current policy unchanged, it searches a bounded reproduction parameter around
the accepted champion. Small maps search the reproduction end round. This is replay-guided
parameter optimization, not neural-network training or recovery of enemy source
code. Observations suggest candidates; they do not prove why a team won.
The available search space covers split thresholds, army size, newborn space,
reserve size and the transition from reproduction to growing long dragons.
It does not invent arbitrary new movement/combat algorithms.

Each candidate is compiled and must pass the existing 12 protocol/strategy smoke
checks, including preserving a long child in a trapped position. It then plays
the frozen current Leviathan on both sides
of every affected map. Promotion requires at least one better result and no worse
result on any affected map/side. Errors, missing replays and timeouts abort the
evaluation without promoting that candidate. Equal scores retain the champion.
Unchanged map groups retain their earlier measured scores.
Candidate evaluation can stop early after a measured regression, or when all
remaining games were already wins and no measured game improved. Unplayed games
are not scored. Baseline and final verification always use the complete schedule.

The game input exposes dimensions but no map name. Maps of the same dimensions
share a deployable policy and are tested together: Big Empty/Help,
Colosseum/Default Small, and the two Queen maps. Evidence remains per-map.
No hidden replay state or opponent identity is supplied to the playing bot.

`--side-aware` adds separate A/B policies using the team letter in the normal
observation. Selectors such as `64x64@A` override a dimension-wide fallback.
Candidate evaluations then run only the affected side of every same-size map;
the baseline and final verification still run all ten maps on both sides.
Use a new output directory when changing policy mode. `--initial-policies FILE`
can seed that new run with validated parameter objects, never previous scores.
`--opponent-binary FILE` copies the exact existing opponent for that new run.
`--cache-dir PATH` reuses checksum-keyed public replay summaries.

## Outputs and continuation

Default output: `benchmark-results/kraken-training/`.

- `champion/`: standalone bot folder, source, generated policy header and executable.
- `checkpoint.json`: accepted parameters, map/side scores, completed candidates,
  source/map hashes, frozen opponent hash and candidate history.
- `evidence.json`: winner/loser pairs per map, series-weighted measurements and rejected files.
- `summary.json`: completed cycles, accepted candidates and current training score.
- `cycle-*/`: candidate source/executable and all match logs/replays.

Leviathan is never weakened or rewritten. Trained parameters always live in the
champion folder. The normal `Kraken/` folder can be updated with a measured champion:

```powershell
# Stop/pause the trainer before this standalone publication command.
python battlecode_data/deploy_kraken.py benchmark-results/kraken-side-campaign
```

Publication verifies source identity, generated policy and protocol checks, backs
up the previous policy/executable, then updates both `Kraken/trained_policy.hpp`
and `Kraken/Kraken.exe`. It audits the generated-function-only identity update;
the trainer regenerates that function from checkpoint parameters before testing.
Use `--publish` on the trainer to automatically publish subsequently accepted
full-campaign champions. Other source changes still require a new campaign.

```powershell
# Continue from the checkpoint for another ten cycles
python battlecode_data/train_kraken.py --cycles 10

# Use existing public replays with no network requests
python battlecode_data/train_kraken.py --offline --cycles 3

# Analyze data only; do not compile or play matches
python battlecode_data/train_kraken.py --offline --analyze-only

# Short end-to-end pilot; use a separate checkpoint from the full map run
python battlecode_data/train_kraken.py --offline --cycles 1 --maps arena --out benchmark-results/kraken-pilot

# Run the resulting bot locally
unswbc run maps/big_empty.map benchmark-results/kraken-training/champion Leviathan
```

Collection defaults to three listing pages and 100 games considered per source
per cycle, including cached games. Top Battles and All Battles have independent
quotas so one cannot starve the other. It does not download all historical battles in one call.
Use the existing downloader's `--start-page` to collect older pages as needed.
Downloads retain the existing public client's throttling and bounded retries.
Use `--interval 300` to space collection cycles; `--cycles` bounds total work.
Network failure stops the cycle; explicit `--offline` uses saved data.
Ctrl+C stops training; rerun the same command to resume. A candidate interrupted
before its checkpoint is evaluated again. A leftover lock after a forced process
kill must be removed only after checking that no trainer is running.

For a checkpoint-boundary pause, create `OUT/stop.request`. The current candidate
finishes and saves its results before the trainer exits. Remove that request file
before resuming. `--stop-file PATH` selects a different request path.
The search rotates parameter families between cycles, excludes small-map-only
parameters on large maps, and avoids previously evaluated policies.
Replay-verified longest-length margins can select near-miss parents for new
proposals, with periodic searches around the champion. Measured regressions are
excluded from that parent pool. A missing game remains unknown, so these parents
are hypotheses, not promoted bots. Only strict map/side score improvement changes
the champion; a better losing margin is never counted as a win.

Source/map/seed changes require a fresh `--out` directory. Do not edit generated
checkpoint files. `--allow-trainer-update` permits only a change to the Python
search driver and records the old/new hashes. `--allow-runner-update` is a separate,
explicit exception for reviewed persistence-only runner fixes that do not change
match execution or scoring; never use it for a rules/schedule change. Bot, map and
protocol changes still require a fresh output directory. Scores are local training results against frozen Leviathan,
not a held-out estimate or a promise of server strength. Repeating deterministic
games is not additional independent evidence. For independent checks, run the
champion against another bot or changed maps using `run_matches.py`; local timing
does not measure judge CPU points. No upload or server submission is performed.

```powershell
python -m unittest discover -s tests -p test_train_kraken.py
```
