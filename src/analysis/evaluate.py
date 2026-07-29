"""Human review sample and agreement measurement.

Two commands:

    python -m src.analysis.evaluate --build     # create the review sample
    python -m src.analysis.evaluate             # score whatever a human filled in

The sample is drawn with a fixed seed and stratified, so it is reproducible and
representative rather than cherry-picked. Human labels live in their own
columns and are never written by this program -- if they are blank, every
metric reports "Not yet evaluated". There is no code path that can produce a
fabricated accuracy score.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
EVAL_DIR = ROOT / "data" / "evaluation"
SAMPLE_FILE = EVAL_DIR / "review_sample.csv"

SEED = 42
SAMPLE_SIZE = 15

MODEL_COLS = ["model_is_relevant", "model_theme", "model_journey_stage",
              "model_feedback_type", "model_severity", "model_confidence"]
HUMAN_COLS = ["human_is_relevant", "human_theme", "human_journey_stage",
              "human_feedback_type", "human_severity"]

# Fields compared. Severity is deliberately excluded from "agreement" headline
# numbers -- it is an ordinal judgment where a 3-vs-4 disagreement is not the
# same kind of error as a wrong theme. It is reported separately.
COMPARED = [
    ("relevance", "model_is_relevant", "human_is_relevant"),
    ("theme", "model_theme", "human_theme"),
    ("journey_stage", "model_journey_stage", "human_journey_stage"),
    ("feedback_type", "model_feedback_type", "human_feedback_type"),
]


def build_sample() -> pd.DataFrame:
    """Stratified, reproducible sample across relevance and theme."""
    records = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))["records"]
    df = pd.DataFrame(records)

    relevant = df[df["is_relevant"]]
    irrelevant = df[~df["is_relevant"]]

    # Match the corpus split (~63% relevant) so relevance can be scored both ways.
    n_rel = round(SAMPLE_SIZE * len(relevant) / len(df))
    n_irr = SAMPLE_SIZE - n_rel

    # Spread the relevant half across themes rather than letting the biggest
    # theme dominate: one per theme first, then fill at random.
    # Select by index rather than groupby.apply -- the latter drops the
    # grouping column in pandas 3, which silently blanks primary_theme.
    picked: list = []
    for theme in sorted(relevant["primary_theme"].dropna().unique()):
        pool = relevant[relevant["primary_theme"] == theme]
        picked.append(pool.sample(1, random_state=SEED).index[0])
    picked = picked[:n_rel]

    remaining = relevant.drop(index=picked)
    n_top_up = max(0, n_rel - len(picked))
    top_up_idx = (remaining.sample(n_top_up, random_state=SEED).index.tolist()
                  if n_top_up else [])

    sample = pd.concat([
        relevant.loc[picked + top_up_idx],
        irrelevant.sample(n_irr, random_state=SEED),
    ])
    sample = sample.sample(frac=1, random_state=SEED).reset_index(drop=True)

    out = pd.DataFrame({
        "feedback_id": sample["feedback_id"],
        "title": sample["title"],
        "description": sample["description"].fillna("").str.slice(0, 600),
        "source_url": sample["source_url"],
        "model_is_relevant": sample["is_relevant"],
        "model_theme": sample["primary_theme"],
        "model_journey_stage": sample["journey_stage"],
        "model_feedback_type": sample["feedback_type"],
        "model_severity": sample["severity"],
        "model_confidence": sample["confidence"],
    })
    for col in HUMAN_COLS:
        out[col] = ""
    out["notes"] = ""
    return out


_BLANK = {"", "nan", "none", "<na>", "null"}


def _filled(df: pd.DataFrame, col: str) -> pd.Series:
    """Rows where a human actually entered something.

    An all-empty column round-trips through CSV as float64 NaN, so check
    notna() first -- a purely string-based test reads "nan" as real content
    and would report a fully-unlabelled sample as fully labelled.
    """
    if col not in df.columns:
        return pd.Series(False, index=df.index)
    s = df[col]
    return s.notna() & ~s.astype(str).str.strip().str.lower().isin(_BLANK)


def score(df: pd.DataFrame) -> dict:
    results: dict = {"sample_size": len(df), "fields": {}, "disagreements": []}

    for label, mcol, hcol in COMPARED:
        mask = _filled(df, hcol)
        n = int(mask.sum())
        if n == 0:
            results["fields"][label] = {"status": "Not yet evaluated", "labelled": 0}
            continue

        sub = df[mask]
        m = sub[mcol].astype(str).str.strip().str.lower()
        h = sub[hcol].astype(str).str.strip().str.lower()
        agree = int((m == h).sum())
        entry = {
            "status": "evaluated",
            "labelled": n,
            "agreements": agree,
            "agreement_rate": round(agree / n, 3),
        }

        # Relevance is binary, so precision/recall are meaningful there.
        if label == "relevance":
            mt = m.isin(["true", "1", "yes"])
            ht = h.isin(["true", "1", "yes"])
            tp = int((mt & ht).sum())
            fp = int((mt & ~ht).sum())
            fn = int((~mt & ht).sum())
            entry["precision"] = round(tp / (tp + fp), 3) if (tp + fp) else None
            entry["recall"] = round(tp / (tp + fn), 3) if (tp + fn) else None
            entry["true_positives"], entry["false_positives"], entry["false_negatives"] = tp, fp, fn

        results["fields"][label] = entry

        for _, row in sub[m.values != h.values].iterrows():
            results["disagreements"].append({
                "feedback_id": row["feedback_id"],
                "title": row["title"][:70],
                "field": label,
                "model": row[mcol],
                "human": row[hcol],
                "model_confidence": row.get("model_confidence"),
                "notes": row.get("notes", ""),
            })

    # Severity reported separately -- ordinal, so exact match is the wrong bar.
    smask = _filled(df, "human_severity")
    if smask.sum():
        sub = df[smask]
        ms = pd.to_numeric(sub["model_severity"], errors="coerce")
        hs = pd.to_numeric(sub["human_severity"], errors="coerce")
        ok = ms.notna() & hs.notna()
        if ok.sum():
            diff = (ms[ok] - hs[ok]).abs()
            results["severity"] = {
                "status": "evaluated",
                "labelled": int(ok.sum()),
                "exact_match": int((diff == 0).sum()),
                "within_one": int((diff <= 1).sum()),
                "mean_abs_error": round(float(diff.mean()), 2),
            }
    else:
        results["severity"] = {"status": "Not yet evaluated", "labelled": 0}

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true",
                        help="create the review sample CSV (overwrites blank labels)")
    args = parser.parse_args()

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    if args.build:
        if SAMPLE_FILE.exists():
            existing = pd.read_csv(SAMPLE_FILE)
            if any(_filled(existing, c).any() for c in HUMAN_COLS):
                print("Refusing to overwrite: review_sample.csv already contains "
                      "human labels. Delete it first if you really want a new sample.")
                return
        sample = build_sample()
        sample.to_csv(SAMPLE_FILE, index=False, encoding="utf-8")
        print(f"Wrote {SAMPLE_FILE.relative_to(ROOT)} with {len(sample)} records "
              f"(seed={SEED}).")
        print("Fill in the human_* columns, then run: python -m src.analysis.evaluate")
        return

    if not SAMPLE_FILE.exists():
        print("No review sample yet. Create one with: "
              "python -m src.analysis.evaluate --build")
        return

    df = pd.read_csv(SAMPLE_FILE)
    results = score(df)
    (EVAL_DIR / "evaluation_report.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"Review sample: {results['sample_size']} records\n")
    for label, entry in results["fields"].items():
        if entry["status"] != "evaluated":
            print(f"  {label:15s}: Not yet evaluated (0 human labels)")
        else:
            line = (f"  {label:15s}: {entry['agreement_rate']:.0%} agreement "
                    f"({entry['agreements']}/{entry['labelled']})")
            if label == "relevance":
                p, r = entry.get("precision"), entry.get("recall")
                line += (f" | precision {p:.2f}" if p is not None
                         else " | precision n/a")
                line += (f" recall {r:.2f}" if r is not None else " recall n/a")
            print(line)

    sev = results.get("severity", {})
    if sev.get("status") == "evaluated":
        print(f"  {'severity':15s}: {sev['exact_match']}/{sev['labelled']} exact, "
              f"{sev['within_one']}/{sev['labelled']} within 1 "
              f"(MAE {sev['mean_abs_error']})")
    else:
        print(f"  {'severity':15s}: Not yet evaluated (0 human labels)")

    if results["disagreements"]:
        print(f"\nDisagreements ({len(results['disagreements'])}):")
        for d in results["disagreements"]:
            print(f"  [{d['field']}] {d['title']}")
            print(f"      model={d['model']!r}  human={d['human']!r}")


if __name__ == "__main__":
    main()
