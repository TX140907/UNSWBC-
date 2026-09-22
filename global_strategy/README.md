# Shared Cthulhu Strategy

The four C++20 headers are the live, global source of Cthulhu's existing strategy.
Changing them changes Cthulhu on its next build. No copies are required for local
`unswbc run maps/default_small.map Cthulhu KrakenSlayer`.

| File | Responsibility |
|---|---|
| map_recognition.hpp | Map families/IDs, observed pearl timers, accumulating Queen/Help evidence, unknown-map fallback |
| opening.hpp | Trophy portal/gap routes and Default Small straight-to-corner, split and center scouting |
| middle_game.hpp | Per-map population/growth policy, pearl regions, mobile patrol, territory, worker movement and economic splitting |
| ending.hpp | Growth cutoff/reserve checks, long-body planning, sprint and emergency split rescue |

This is an extraction, not new training. Other maps retain their existing generic
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
