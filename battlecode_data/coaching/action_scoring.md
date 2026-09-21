# Action scoring

Local replay audit + empirical action scoring. No bot changes or downloads.

Outcome score (0..100): 60 for surviving lineage at R+10, 30 for retained
longest length, 10 for up to four net new segments. Later splits count through
descendants, but children born before the action do not. Censor final 10 rounds.
This is a declared heuristic, not a causal estimate of unplayed alternatives.


Uniform deterministic reservoir: up to 1,500 actions per match, both sides, then exclude the final 10 rounds. Own series are entirely excluded from fitting. Every fifth sorted public series is validation; no turn-level random split. Features only use pre-action 7x7 observations and own public state. Opponent pressure is visible contact, not an inferred hidden source-code strategy.

Prediction needs >=30 samples from >=3 training series; otherwise no estimate. The model estimates outcomes of observed action classes; it cannot prove an unplayed direction or split would win. Legal-action checking must precede any use in a bot.

```json
{
  "training_series": 19,
  "validation_series": 5,
  "own_series_excluded": 6,
  "train_samples": 105450,
  "validation_samples": 31249,
  "covered": 30753,
  "mae": 14.906899388556571,
  "baseline_mae": 18.546836763598773
}
```

The model is an offline review tool, not installed in Leviathan. An action with a low score may have had no good alternative. Long-term match victory is not the same objective as this 10-round score.
