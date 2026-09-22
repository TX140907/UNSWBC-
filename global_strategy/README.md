# Shared Cthulhu Strategy

Big Empty's shared `big_emptyOpening` runs emergency head rescue before expansion
(also inherited by Help). This is not a Cthulhu-specific dispatch hook. If no
immediate head move is legal, the existing survival planner can split length-2
segments into a reversed long child, leaving two at the old head. A known tail
must have a simulated escape; an unseen tail remains a last-chance rescue.
This requires a free unit slot and cannot override the 64-unit cap.

## Short-unit Head Trades

From round 40, `headTradeAction` takes priority over expansion in shared Big Empty
strategy (and its Help alias), after emergency rescue. Both `big_emptyOpening`
and `big_emptyMiddleGame` invoke it; other maps do not. Cthulhu only dispatches
the shared stages and has no private rescue or head-trade hook.
Dragons of length at most 8, with at least one surviving teammate, may trade
into a visible enemy head one move or a two-step sprint away. The enemy must
have at least 6 currently visible segments and at least 2 more than the attacker.
Visible segments are only a lower bound on enemy length. Unknown edges, blocked
intermediate tiles and incomplete own bodies are excluded. This is a local
opportunity attack, not a coordinated pursuit or a claim to know the enemy's
longest dragon. Engine probes confirm both heads die regardless of length.
No new win-rate benchmark has been run for this policy.

## Current Recognition Status

Large-map expansion: Big Empty (and the shared Help strategy) prioritizes splitting
two-segment children until 64 living units, respecting a smaller controller limit.
There is no round cutoff; losses can trigger replenishment. When split is not
available, prefer a safe two-step sprint that collects enough food to cover its
length cost, without sacrificing an available next-turn split. At capacity the
existing movement/long-body planner resumes. This does not guarantee child survival.

The named-map trainer defaults to `--suite competition`: Arena, Big Empty,
Colosseum, Default, Default Small, Queen of Spades, Schooltime, Trophy (16 A/B games).
Help and Aged Queen are excluded even from shared-dimension regression matches.
`--suite full` explicitly restores the old ten-map scope. Use a fresh checkpoint
when changing scope; a 16/16 result is not a historical 20/20 verification.

Temporary shared strategy: Help and Big Empty both select strategy ID 2 in
opening, middle-game and endgame, using Big Empty's weights for the current side.
Every 64x64 dragon, including a newborn, can select this strategy on its first
observation without resolving the exact map. Exact identity/candidate evidence
is retained separately for diagnostics; contradictory evidence still falls back
to generic. The help entry points delegate to the big_empty entry points.
Historical Help weights remain in the configuration but are not selected.

64x64 initial recognition uses UNIT_COUNT (<=5 = Big Empty, >=6 = Help) for
IDs 0..5 with matching team parity at round 0: the first three originals per team.
The result is stored once; later count changes are not used to reclassify it.
This assumes Help's protected opening loses no units before those originals act.
Other originals use their own round-0 ID/team/position/length in the spawn tables.
Newborns and later rounds use observation-based fallback. Terrain/timer evidence
can still flag a contradiction instead of silently overriding it with live counts.
Tests cover both sides, boundary counts 5/6 and earlier teammates splitting.

`MapStatus` retains the candidate mask, evidence type, first identification round
and separate `opening`, `middle`, `ending` map statuses. Every observation updates
all three. Map 0 selects generic weights and generic movement; it no longer
silently selects a named map from a shared dimension. A contradictory signature
invalidates the identification and returns all stages to generic.

Within the ten-map repository catalogue, Arena, Default, Schooltime and Trophy
are dimension-unique. Default Small and Colosseum now have edge-type signatures
visible from all initial spawns: tests confirm identification without moving or
waiting for pearl timers. Signatures ignore portal color/ID.
Big Empty requires a distinguishing observed edge or a timer above Help's maximum
20; merely seeing open water is insufficient. Ambiguous early dragons can safely
approach the nearest selected distinguishing edge. This heuristic is not a proof
of the globally shortest safe scouting route.

Queen variants have overlapping timer distributions. Exact identity can remain
unknown, but both now select the shared Queen strategy (ID 7) immediately from
25x35 dimensions. All three Aged Queen entry points delegate to ordinary Queen;
both use the ordinary Queen profile for the current side. Existing ID 8 weights
are retained as historical configuration but are not selected by Cthulhu.
`MapStatus.map` records exact identity; stage statuses record strategy identity.
No universal finite minimum can be promised for exact variant recognition. Signatures
assume the known catalogue, not arbitrary custom maps of identical dimensions.

The new recognition changes behavior. The old 120-case equivalence test covers
the extracted planner with manually supplied legacy evidence, not equivalence
of the new online recognition. New status and catalogue tests cover that change.

## Opponent Evidence

Selected opponent: dev test 1 :P, team 545. Public replay evidence and the opening
study are in `battlecode_data/top1_replays/`. The initial sample has 23 matches,
eight maps, all opponent-side B, with submission IDs and replay checksums retained.
It is not a runnable opponent or proof that an observed opening is optimal.
No new online challenges or automatic promotion have been performed.

```powershell
python battlecode_data/download_team_public.py --team-id 545 --out battlecode_data/top1_replays
python battlecode_data/study_top_openings.py --replays battlecode_data/top1_replays --team-id 545 --out battlecode_data/top1_replays/opening-study.json
```

These are bounded refresh/analysis commands, not an unattended training service.
New direct battles require authenticated Battlecode access or an authorized local
opponent artifact. Keep A/B and submission versions separate when testing ideas.

The four C++20 headers are the live, global source of Cthulhu's existing strategy.
Changing them changes Cthulhu on its next build. No copies are required for local
`unswbc run maps/default_small.map Cthulhu KrakenSlayer`.

| File | Responsibility |
|---|---|
| map_recognition.hpp | Map families/IDs, observed pearl timers, accumulating Queen/Help evidence, unknown-map fallback |
| opening.hpp | Trophy portal/gap routes and Default Small straight-to-corner, split and center scouting |
| middle_game.hpp | Per-map population/growth policy, pearl regions, mobile patrol, territory, worker movement and economic splitting |
| ending.hpp | Growth cutoff/reserve checks, long-body planning, sprint and emergency split rescue |

The original modules were an extraction, not new training. Recognition has since
changed as described above. Other maps retain their existing generic
opening through the middle-game policy; no unimplemented map-specific opening is
invented. Map IDs 1..10 are Arena, Big Empty, Colosseum, Default, Default Small,
Help, Queen, Aged Queen, Schooltime, Trophy. ID 0 means not identified.
Some existing dimension/timer classifiers are heuristic, not proof of map identity.

Safety is not restricted to endgame. `longBodyAction` also handles an early-game
fallback, and opening actions still call the bot's collision/search checks.
Trophy uses left-right reflection; Default Small uses central reflection.
Portal IDs are read from observed edges, not inferred from the other team's color.

## Reuse

The headers use `namespace global_strategy`, templates and caller-owned state.
There is no shared mutable memory between dragons. A C++ bot supplies an adapter
with Cthulhu's observation/state fields and its movement/search primitives. See
the short forwarding methods in `Cthulhu/main.cpp` for the working adapter.
`SearchState`, `advance`, `search`, `area`, `tuning`, body memory and collision
checks remain engine responsibilities, not duplicated in the global files.

Typical dispatch after updating observations:

```cpp
bot.planTerritory(ct);
std::vector<int> action;
if (!global_strategy::trophyOpening(bot, ct, action) &&
    !global_strategy::smallOpening(bot, ct, action)) {
    action = global_strategy::middleGameAction(bot, ct);
    if (action.empty()) action = global_strategy::longBodyAction(bot, ct);
}
```

Weights remain independently trainable per map AND side in
`Cthulhu/map_policies.json`, compiled into `trained_policy.hpp` and exposed through
the adapter's `tuning()`. Reusing these algorithms does not force every bot to use
identical trained weights. Kraken, KrakenSlayer, mybot and NamBot are unchanged;
Python bots need a separate adapter/port rather than directly importing C++.

## Frozen Training And Packaging

Export a self-contained copy before isolated training or submission:

```powershell
python battlecode_data/shared_strategy.py --source Cthulhu --out benchmark-results/cthulhu-export-new
```

The destination must not exist. It includes all four modules in a local
`global_strategy/` subdirectory. Local snapshot modules take priority over the
live global directory, so later global edits cannot change a frozen experiment.
The named-map trainer, general trainer and frozen-matchup verifier now copy and
hash these dependencies. Older ad-hoc scripts that copy only `main.cpp` must use
the exporter or `shared_strategy.snapshot(source, destination)` too.

Verification: `python tests/run_tests.py --suite unit`. The additional
`tests/global_strategy_equivalence.cpp` compares 120 map/side/phase decisions
against `tests/baselines/cthulhu-before-global`, the pre-extraction source fixture.
