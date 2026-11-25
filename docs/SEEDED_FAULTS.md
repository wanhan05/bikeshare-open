# Seeded faults

Seeded by hand, one at a time on a clean tree, by scripts/commands run in
the terminal. The local agent (qwen3.5:9b via Ollama) exhausted memory on a
16 GB M2 MacBook Air and froze the machine, and the hosted fallback models
required paid credits, so no agent turns are counted here. The hook was
triggered with the same JSON payload Claude Code sends after an Edit.
All output below is pasted verbatim.

## Exercise 1: the cnt_lag_2 test, written first

Committed before the feature existed (see git log). It failed for the right reason: the column did not exist yet.

make test before implementing cnt_lag_2:
```
E       AttributeError: 'Series' object has no attribute 'cnt_lag_2'. Did you mean: 'cnt_lag_1'?

.venv/lib/python3.12/site-packages/pandas/core/generic.py:6194: AttributeError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_cnt_lag_2_is_a_true_two_day_calendar_lag
1 failed, 15 passed in 1.84s
```

## Fault 1: forbidden column added to feature_columns

Change:
```
diff --git a/src/features.py b/src/features.py
index 2659ccd..67590ba 100644
--- a/src/features.py
+++ b/src/features.py
@@ -83,7 +83,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

PostToolUse hook (exit code and stderr):
```
exit code: 2
Leakage tests failed after editing /Users/wanhansun/Downloads/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_2', 'cnt_lag_7', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 8 passed in 0.80s
```

make test:
```
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_2', 'cnt_lag_7', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 1.76s
make: *** [test] Error 1
```

After restoring (git checkout -- src/features.py):
```
17 passed in 1.13s
```

Caught by test_no_forbidden_features. It guards the gate rather than the data, which is exactly the edit it exists to catch.

## Fault 2: .shift(1) deleted from cnt_roll_7

Change:
```
diff --git a/src/features.py b/src/features.py
index 2659ccd..7027c67 100644
--- a/src/features.py
+++ b/src/features.py
@@ -75,7 +75,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # Our own, tested version of the mirror's unverified cnt_2d_bfr.
     out["cnt_lag_2"] = out[TARGET].shift(2)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
 
```

PostToolUse hook (exit code and stderr):
```
exit code: 2
Leakage tests failed after editing /Users/wanhansun/Downloads/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 8 passed in 0.33s
```

make test:
```
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 1.33s
make: *** [test] Error 1
```

After restoring (git checkout -- src/features.py):
```
17 passed in 1.12s
```

Caught by test_rolling_mean_excludes_today: without the shift the 7-day mean includes the day being predicted.

## Fault 3: weather encoder's raise removed

Change:
```
diff --git a/src/features.py b/src/features.py
index 2659ccd..2a8d8d2 100644
--- a/src/features.py
+++ b/src/features.py
@@ -27,7 +27,7 @@ def encode_weather(series: pd.Series) -> pd.Series:
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
     if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
+        pass  # raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

PostToolUse hook (exit code and stderr):
```
exit code: 2
Leakage tests failed after editing /Users/wanhansun/Downloads/bikeshare-open/src/features.py:
........F                                                                [100%]
=================================== FAILURES ===================================
__________________ test_encode_weather_rejects_unknown_labels __________________

    def test_encode_weather_rejects_unknown_labels():
        """Without the raise, an unseen label becomes NaN and a later dropna
        deletes the row silently. The current data has no unseen labels, so
        only a direct test can see this fault."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:88: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 8 passed in 0.34s
```

make test:
```
        """Without the raise, an unseen label becomes NaN and a later dropna
        deletes the row silently. The current data has no unseen labels, so
        only a direct test can see this fault."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:88: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 16 passed in 1.25s
make: *** [test] Error 1
```

After restoring (git checkout -- src/features.py):
```
17 passed in 1.14s
```

The starter suite cannot see this fault: the current data has only GOOD/MISTY/BAD, so removing the raise changes no row and every pipeline test stays green. It is caught only by test_encode_weather_rejects_unknown_labels, added in this repo, which feeds the encoder an unseen label directly.

## Fault 4: cp into data/raw/ from Bash

Command (changes temp on 2011-01-03, then copies over the raw file):
```
sed 's/1.229108/9.999999/' data/raw/bike_daily.csv > /tmp/bike.csv && cp /tmp/bike.csv data/raw/bike_daily.csv
```

git diff --stat:
```
 data/raw/bike_daily.csv | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

make test (full suite, before any hash check):
```
17 passed in 1.08s
```

Nothing went red. The PostToolUse hook never fired, because its matcher is
`Edit|Write` and this was a Bash call. The deny rules
`Edit(./data/raw/**)` and `Write(./data/raw/**)` bind the agent's file
tools, not a `cp` inside Bash (Claude Code's own /status also reports that
the `Write(...)` deny rule is not matched by file permission checks at all).
The tests check properties of the data, and a changed temperature on one
day violates none of them.

What would catch it: a hash check on the raw file (implemented below as
test_raw_file_is_unmodified in tests/test_contract.py), a filesystem
permission (`chmod -w data/raw`), a PreToolUse hook on Bash that rejects
commands writing to data/raw, or a Stop hook running `make test` once the
hash test exists.

make test after adding test_raw_file_is_unmodified:
```
E         - a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
E         + ab5f25d091adc19e631dec48ed8e380544b3b6629dee13a53736a2db1f4b932d

tests/test_contract.py:82: AssertionError
=========================== short test summary info ============================
FAILED tests/test_contract.py::test_raw_file_is_unmodified - AssertionError: ...
1 failed, 17 passed in 1.12s
make: *** [test] Error 1
```

After restoring the raw file:
```
18 passed in 1.04s
```
