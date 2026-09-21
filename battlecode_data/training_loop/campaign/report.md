# Bounded Leviathan learning loop

Budget: 3 rounds, 20 total unranked games (7 / 7 / 6), rank radius 12.
Sent: 20/20 games. Completed results: {'win': 10, 'loss': 10, 'draw': 0}.
Training proposes map-size pressure-risk weights from own single-step action outcomes. Local Kraken matches gate regressions on affected maps, not generalization to every opponent. Each round faces different opponents/maps; online win rates are not a paired before/after test.

| Round | State | Submission | Local decision | Online W/L/D | Battle IDs |
|---|---|---|---|---|---|
| [1](round1/fit.json) | done | 632 | passed local gate | {'win': 4, 'loss': 3, 'draw': 0} | [9162, 9163, 9164, 9165, 9167, 9168, 9170] |
| [2](round2/fit.json) | done | 641 | passed local gate | {'win': 3, 'loss': 4, 'draw': 0} | [9393, 9394, 9395, 9396, 9397, 9398, 9399] |
| [3](round3/fit.json) | done | 649 | passed local gate | {'win': 3, 'loss': 3, 'draw': 0} | [9590, 9776, 9777, 9778, 9779, 9780] |

## Replay reports

- [Round 1: results and replays](round1/replays/report.md); learned proposal: `{'11x11/short': 1.093}`.
- [Round 2: results and replays](round2/replays/report.md); learned proposal: `{'11x11/short': 1.14}`.
- [Round 3: results and replays](round3/replays/report.md); learned proposal: `{'11x11/short': 1.132}`.

The last round's replays are retained for the next training campaign; this campaign stops after three fits.
