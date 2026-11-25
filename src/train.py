"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import json

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


# Exercise 4. Optional target transformations, behind a flag. Each pair is
# (forward, inverse); the inverse uses only columns known at prediction time.
# The committed reports/metrics.json is always the untransformed pipeline.
TARGET_TRANSFORMS = {
    # Ratio to the trailing 7-day mean: the model predicts relative change
    # around the recent level, so a tree no longer has to extrapolate the
    # 2011 -> 2012 growth in absolute counts.
    "ratio_roll7": (
        lambda d: d[TARGET] / d["cnt_roll_7"],
        lambda d, p: d["cnt_roll_7"].to_numpy() * p,
    ),
}


def fit_and_score(transform: str | None = None) -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    fwd, inv = TARGET_TRANSFORMS.get(transform, (lambda d: d[TARGET], lambda d, p: p))
    if transform:
        results["target_transform"] = transform
    for name, model in MODELS.items():
        if transform and name.startswith("baseline"):
            # Baselines predict counts directly; transforming them is meaningless.
            model.fit(train[cols], train[TARGET])
            predict = lambda part, m=model: m.predict(part[cols])
        else:
            model.fit(train[cols], fwd(train))
            predict = lambda part, m=model: inv(part, m.predict(part[cols]))
        results[name] = {}
        for split, part in [("valid", valid), ("test", test)]:
            pred = predict(part)
            results[name][split] = {
                "r2": round(float(r2_score(part[TARGET], pred)), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], pred)), 1),
            }
    return results


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--target-transform", choices=sorted(TARGET_TRANSFORMS))
    args = ap.parse_args()
    res = fit_and_score(args.target_transform)
    out = METRICS
    if args.target_transform:  # never overwrite the committed, untransformed metrics
        out = METRICS.with_name(f"metrics_{args.target_transform}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
