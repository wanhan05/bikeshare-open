# Bikeshare demand: an audited forecasting pipeline

Wanhan Sun, DSC 180A, Methodology Assignment 6. Repository:
https://github.com/wanhan05/bikeshare-open. Every number below is reproduced by
`make all` from a clean checkout and matches `reports/metrics.json`.

## Results

Daily total rides (`cnt`), trained on 2011 (348 days), validated on H1 2012
(182 days), tested once on H2 2012 (184 days). "Before" is the starter
pipeline (14 features); "after" adds my feature `cnt_lag_2` (15 features).
R² is computed against each split's own mean.

| Model | Features | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | after | 0.6453 | 833.4 | 0.583 | 945.5 |
| hgb | after | 0.2481 | 1269.8 | -0.4737 | 1947.9 |

The "after" rows are the committed `reports/metrics.json`. The baselines do not
use the new feature, so their rows are identical by construction.

## Headline finding

The naive evaluation, a model handed every column, scores test R² = 1.000
(`python -m src.leakage_demo`) and is invalid: `casual + registered == cnt` on
every row, so it has learned addition. Under a temporal split the mean baseline
is strongly negative (test R² -2.14), because ridership grew about 65% from
2011 to 2012 and the 2011 average is a poor guess for late 2012. Ridge reaches
test R² 0.583 against a persistence baseline of 0.510, an honest margin of
0.07, and it loses to persistence on MAE (945.5 vs 840.1 rides). Gradient
boosting is negative on test (-0.47) while still far better than the mean
baseline: a tree cannot predict above the largest count it saw in training,
and 56% of test days exceed the 2011 maximum of 6,043 rides. My feature,
`cnt_lag_2`, moved validation R² by -0.002 for ridge (inside the noise for a
182-day validation set) and +0.030 for gradient boosting. I kept it, because it
replaces the mirror's unverified `cnt_2d_bfr` with a lag whose alignment is
tested, not because it improved the headline model.

## Exercise 4: target transformation

The tree fails because it is asked to predict absolute counts on a growing
series. I tried four transformations on the validation set only: `log(cnt)`,
`cnt - cnt_lag_1`, `cnt - cnt_roll_7`, and `cnt / cnt_roll_7`, inverting each
prediction back to counts before scoring.

| hgb target | Valid R² | Valid MAE |
|---|---|---|
| cnt (committed pipeline) | 0.2481 | 1269.8 |
| log(cnt) | 0.1645 | 1335.6 |
| cnt - cnt_lag_1 | 0.6057 | 843.7 |
| cnt - cnt_roll_7 | 0.7228 | 714.1 |
| cnt / cnt_roll_7 | 0.7527 | 677.9 |

The log does not help, because it compresses the scale but is still a level
that grows. Predicting change relative to the trailing 7-day mean does: the
model learns how weather and calendar move demand around its recent level, and
the level itself carries the trend. I chose `cnt / cnt_roll_7` on validation
and then touched the test set once (`python -m src.train --target-transform
ratio_roll7`): hgb test R² 0.6247, MAE 831.2, which is better than ridge (0.583,
945.5) and slightly better than persistence on MAE (840.1).

Is it defensible? Mostly yes. The inverse uses only `cnt_roll_7`, which is
shifted before it aggregates and is known at prediction time, so nothing leaks,
and modelling relative change is the standard answer to a trend rather than a
trick. Two caveats keep it from being a clean win. First, it was the best of
four options on 182 validation days, so part of its margin is selection. Second,
much of the gain comes from the transformation itself: simply predicting
`cnt_roll_7` scores 0.5945 on validation and 0.4796 on test, so the tree adds
about 0.15 R² on top of a baseline the transformation hands it. A fair
comparison would give ridge the same target (on validation it gets worse, 0.39),
and would report the 7-day-mean baseline alongside persistence. The committed
`reports/metrics.json` is the untransformed pipeline.

One correction to the tutorial: it says H1 2012 is "largely within range" of
2011. In this data 39% of validation days exceed the 2011 maximum (against 56%
of test days), so out-of-range targets do explain part of the weak validation
score too.

## Exercise 5: ridge vs persistence

Ridge is not worth deploying over "yesterday again" as it stands. It wins on R²
(0.583 vs 0.510 on test) only because it avoids persistence's worst misses: on
the 17 test days where demand moved more than 2,000 rides from the day before,
ridge's MAE is 1,862 against persistence's 3,019. On every other day it is
worse (MAE 852 vs 618), and it is closer than persistence on only 39% of test
days; its median absolute error is 894 rides against 507. The reason is a
systematic bias: ridge under-predicts by 553 rides on average in H2 2012
(persistence: -16), because its intercept and weather coefficients are fitted
on 2011 levels. Its largest standardised coefficients are `cnt_roll_7` (458)
and `cnt_lag_1` (348), so it is mostly a smoothed persistence model plus a
weather adjustment (`weather_severity` -282, `temp` +185). The weather
adjustment is the part worth keeping. A deployment I would defend is
persistence (or the 7-day mean) corrected by a weather model fitted on the
residual, which removes the level bias instead of learning it from the wrong
year.

## Attribution

Models used: `qwen3.5:9b` via Ollama, 64k context (`bikeshare-coder`), on a
16 GB M2 MacBook Air. It produced the availability argument for my first
feature idea and then exhausted memory and froze the machine. I tried the
hosted fallback: `qwen3.5:27b-cloud` was not available on my Ollama account,
and `gpt-oss:120b` and `gpt-oss:20b` returned HTTP 402 (paid credits required).
I did not pay, so the local agent did very little of the typing. Instead, most
of the code in my diff was written by Claude (Anthropic's claude.ai assistant,
not through Claude Code), working from the starter code and my test output.

Generated by an agent or assistant:
- qwen3.5:9b: the availability argument for `temp_x_hum` (which I rejected, see
  DECISIONS.md).
- Claude: `test_cnt_lag_2_is_a_true_two_day_calendar_lag`,
  `test_encode_weather_rejects_unknown_labels`, `cnt_lag_2` in
  `src/features.py`, `test_every_raw_column_is_classified` with `SOURCE_COLS`
  and `RAW_FEATURE_COLS`, `test_raw_file_is_unmodified` with `RAW_SHA256`, the
  `seed-fault` skill, the script that seeded the faults and wrote
  `docs/SEEDED_FAULTS.md`, the `--target-transform` flag in `src/train.py`, and
  first drafts of this report and the new DECISIONS.md lines.
- The starter pipeline itself (everything in the first commit) was provided by
  the course.

Decisions that were mine (each is a line in docs/DECISIONS.md):
- Which feature to add (`cnt_lag_2` over `temp_x_hum`) and whether to keep it.
- That same-day weather counts as available only as a forecast, rejecting the
  agent's claim that it is recorded before the count.
- That raw columns are classified by an allowlist, not by the feature denylist.
- That the raw file is protected by a hash test, not only by permission rules.
- Which target transformation to keep, chosen on validation, with test touched
  once.
- Whether ridge is worth deploying over persistence.
- Running the seeded faults by hand rather than paying for a hosted model.

I am accountable for every number in this report.
