# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25. Setup: `make model` failed (`ollama create -f -` is not accepted by my Ollama version); built `bikeshare-coder` from a temp Modelfile. Makefile left as is, since `make all` does not use it.
- 2026-11-25. Starter `new-feature` skill blocked its own `!python -c` feature-list command; added `Bash(python -c*)` to its allowed-tools.
- 2026-11-25. Claude Code `/status` reports `Write(./data/raw/**)` in settings.json is never matched (only Edit rules apply). Left unchanged; the Edit rule covers file tools, and Fault 4 shows neither binds Bash.
- 2026-11-25. Rejected the agent's availability argument for `temp_x_hum` ("weather is recorded before the count"): daily weather is a same-day average, so it is available only as a forecast, the assumption every weather feature here already makes.
- 2026-11-25. Feature: chose `cnt_lag_2` over `temp_x_hum` (valid ridge +0.0018, and it cannot be tested against earlier dates). Availability: cnt on d-2 is known at d. Valid R^2 ridge 0.6475 -> 0.6453 (-0.0022, noise), hgb 0.2185 -> 0.2481 (+0.0296). Kept: it is a tested replacement for `cnt_2d_bfr`, which matches it on all 714 rows but stays excluded.
- 2026-11-25. Classify raw columns by declaration (`SOURCE_COLS`, `RAW_FEATURE_COLS` allowlist), not by `feature_columns()`: the denylist let a new numeric raw column count as a feature and pass.
- 2026-11-25. Added `test_encode_weather_rejects_unknown_labels`: the starter suite stays green with the encoder's raise removed, because the data has no unseen labels.
- 2026-11-25. Local agent froze a 16 GB machine; hosted fallbacks needed paid credits. Seeded the four faults by hand with a script; no agent turn counts.
- 2026-11-25. Fault 4: added `RAW_SHA256` and `test_raw_file_is_unmodified`; a Bash `cp` into data/raw passes every permission rule and the hook.
- 2026-11-25. Exercise 4: chose `cnt / cnt_roll_7` for hgb on validation over log, diff-lag-1 and diff-roll-7 (valid R^2 0.2481 -> 0.7527). Test touched once afterwards: 0.6247. Behind `--target-transform`; committed metrics stay untransformed.
- 2026-11-25. Exercise 5: ridge not worth deploying over persistence as is (closer on 39% of test days, +553 ride bias); weather adjustment on top of persistence instead.
- 2026-11-25. CLAUDE.md: added the raw-column classification and raw-hash rules and the `seed-fault` skill.
