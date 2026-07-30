"""Deterministic aggregation and priority scoring.

Every number the dashboard shows is computed here, in plain Python, from the
classified records. No LLM is involved at this stage -- the model read and
categorised the feedback; pandas does the arithmetic. That split is the point:
counts and rankings must be reproducible and auditable, and an LLM is neither.

    python -m src.analysis.aggregate
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "data" / "processed"

# Priority weights. Deliberately few, deliberately explainable.
W_DEMAND, W_FREQUENCY, W_SEVERITY = 0.45, 0.30, 0.25

# Skew threshold from DATA_PLAN.md, fixed in advance so the choice of scale is
# made by the data rather than by whoever wants a nicer-looking chart.
LOG_SCALE_THRESHOLD = 10.0

HIGH_SEVERITY = 4

# Analyst recommendations. These are JUDGMENT, not data -- labelled as such in
# the UI so a reader can always tell which is which.
RECOMMENDED_ACTIONS: dict[str, str] = {
    "Action discovery & organization":
        "Improve action search, categories, naming and catalog organization so "
        "users can quickly find the correct action.",
    "Context, targeting & pre-fill":
        "Use the originating page and entity context to pre-select known targets "
        "and reduce repeated input.",
    "Form structure, input types & controls":
        "Expand form controls and make long or complex forms easier to structure "
        "and complete.",
    "Dynamic & dependent inputs":
        "Allow form fields, options and defaults to adapt dynamically to "
        "previous selections and context.",
    "Validation & error guidance":
        "Provide flexible validation rules and clear, actionable explanations "
        "before submission.",
    "Backend & invocation configuration":
        "Make backend connections, payload mapping, credentials and invocation "
        "settings easier to configure.",
    "Permissions, eligibility & action visibility":
        "Evaluate eligibility earlier and clearly control which users can see "
        "and run each action.",
    "Approval workflows & governance":
        "Support flexible approval routing and governance rules based on risk, "
        "environment, team and action type.",
    "Testing, editing & drafts":
        "Improve safe action creation with previews, test runs, drafts, "
        "versioning and unsaved-change protection.",
    "Execution visibility, notifications & run control":
        "Centralize run status, logs, notifications, retries and controls in the "
        "execution experience.",
    "Multi-step & orchestration":
        "Support reliable multi-step execution, branching, data transfer and "
        "coordination across systems.",
}


def load_records() -> pd.DataFrame:
    data = json.loads((PROC_DIR / "analyzed.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(data["records"])
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    return df


def relevant_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["is_relevant"]].copy()


def _share_of_max(series: pd.Series) -> pd.Series:
    """Scale so the leading theme is 1.0 and everything else is its share.

    Chosen over min-max because min-max forces the lowest theme to exactly 0
    on every axis, which manufactures spread that is not in the data --
    especially for severity, which clusters tightly in this dataset.
    """
    top = series.max()
    return series / top if top else series * 0.0


def choose_vote_scale(theme_votes: pd.Series) -> tuple[str, float]:
    """Pick linear or log scaling from the data, using a threshold set in advance."""
    median = theme_votes.median()
    ratio = (theme_votes.max() / median) if median else float("inf")
    return ("log" if ratio > LOG_SCALE_THRESHOLD else "linear"), float(ratio)


def theme_table(rel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Rank themes by the transparent priority score."""
    g = rel.groupby("primary_theme").agg(
        posts=("feedback_id", "count"),
        total_votes=("votes", "sum"),
        avg_severity=("severity", "mean"),
        avg_confidence=("confidence", "mean"),
    ).reset_index()

    scale, ratio = choose_vote_scale(g["total_votes"])
    votes_basis = g["total_votes"].apply(math.log1p) if scale == "log" else g["total_votes"]

    g["demand_score"] = _share_of_max(votes_basis)
    g["frequency_score"] = _share_of_max(g["posts"])
    g["severity_score"] = _share_of_max(g["avg_severity"])
    g["priority_score"] = (
        W_DEMAND * g["demand_score"]
        + W_FREQUENCY * g["frequency_score"]
        + W_SEVERITY * g["severity_score"]
    )

    g["recommended_action"] = g["primary_theme"].map(RECOMMENDED_ACTIONS).fillna("")
    g = g.sort_values("priority_score", ascending=False).reset_index(drop=True)
    g["rank"] = g.index + 1

    meta = {
        "vote_scale": scale,
        "vote_skew_ratio": round(ratio, 2),
        "threshold": LOG_SCALE_THRESHOLD,
        "weights": {"demand": W_DEMAND, "frequency": W_FREQUENCY, "severity": W_SEVERITY},
        "explanation": (
            f"Priority = {W_DEMAND:.0%} vote demand + {W_FREQUENCY:.0%} how often the "
            f"theme appears + {W_SEVERITY:.0%} average severity. Each part is scaled "
            f"so the highest-scoring theme = 1.0. Votes use a {scale} scale because "
            f"the top theme has {ratio:.1f}x the votes of the median theme "
            f"(log applies above {LOG_SCALE_THRESHOLD:.0f}x)."
        ),
    }
    return g, meta


def stage_table(rel: pd.DataFrame) -> pd.DataFrame:
    """Where friction sits across the Action Configuration journey."""
    from ..models.taxonomy import STAGE_NAMES

    g = rel.groupby("journey_stage").agg(
        posts=("feedback_id", "count"),
        total_votes=("votes", "sum"),
        avg_severity=("severity", "mean"),
    ).reset_index()

    # Keep the journey in its real order, and show stages with no feedback
    # rather than silently dropping them -- an empty stage is a finding.
    order = {name: i for i, name in enumerate(STAGE_NAMES)}
    missing = [s for s in STAGE_NAMES if s not in set(g["journey_stage"])]
    if missing:
        g = pd.concat([g, pd.DataFrame(
            {"journey_stage": missing, "posts": 0, "total_votes": 0, "avg_severity": 0.0}
        )], ignore_index=True)

    g["stage_order"] = g["journey_stage"].map(order)
    g["votes_per_post"] = (g["total_votes"] / g["posts"]).replace([float("inf")], 0).fillna(0)
    return g.sort_values("stage_order").reset_index(drop=True)


def evidence_for_theme(rel: pd.DataFrame, theme: str, n: int = 3) -> list[dict]:
    """Highest-demand records for a theme that carry a verified quote."""
    subset = rel[(rel["primary_theme"] == theme) & (rel["evidence_verified"])]
    subset = subset.sort_values("votes", ascending=False).head(n)
    return subset[["title", "votes", "severity", "evidence_excerpt",
                   "source_url", "journey_stage"]].to_dict("records")


def kpis(df: pd.DataFrame, rel: pd.DataFrame, themes: pd.DataFrame) -> dict:
    return {
        "records_collected": int(len(df)),
        "relevant_posts": int(len(rel)),
        "total_votes": int(rel["votes"].sum()),
        "high_severity_posts": int((rel["severity"] >= HIGH_SEVERITY).sum()),
        "most_common_theme": themes.sort_values("posts", ascending=False)
                                   .iloc[0]["primary_theme"],
        "highest_priority_theme": themes.iloc[0]["primary_theme"],
        "low_confidence_posts": int((rel["confidence"] < 0.7).sum()),
        "unverified_evidence": int((~rel["evidence_verified"]).sum()),
    }


def build_all() -> dict:
    df = load_records()
    rel = relevant_only(df)
    themes, scoring_meta = theme_table(rel)
    stages = stage_table(rel)
    return {
        "kpis": kpis(df, rel, themes),
        "scoring": scoring_meta,
        "themes": themes.to_dict("records"),
        "stages": stages.to_dict("records"),
        "evidence": {t: evidence_for_theme(rel, t) for t in themes["primary_theme"]},
    }


def main() -> None:
    out = build_all()
    (PROC_DIR / "aggregates.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    k = out["kpis"]
    print("KPIs")
    for key, val in k.items():
        print(f"  {key:24s}: {val}")
    print()
    print(out["scoring"]["explanation"])
    print()
    print(f"{'#':>2}  {'theme':34s} {'posts':>5} {'votes':>6} {'sev':>4} {'score':>6}")
    for r in out["themes"]:
        print(f"{r['rank']:>2}  {r['primary_theme'][:34]:34s} {r['posts']:>5} "
              f"{r['total_votes']:>6} {r['avg_severity']:>4.1f} {r['priority_score']:>6.3f}")
    print()
    print(f"{'stage':38s} {'posts':>5} {'votes':>6} {'v/post':>7}")
    for r in out["stages"]:
        print(f"{r['journey_stage'][:38]:38s} {r['posts']:>5} {r['total_votes']:>6} "
              f"{r['votes_per_post']:>7.1f}")
    print(f"\nWrote {(PROC_DIR / 'aggregates.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
