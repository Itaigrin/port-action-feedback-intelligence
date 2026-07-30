# Human review

`review_sample.csv` holds 15 records for manual checking. **No scores exist until a
human fills it in** — every metric reports "Not yet evaluated" until then, and there
is no code path that can produce a number without real labels.

## How the sample was drawn

- **Fixed seed (42)**, so the same 15 records come out on every run.
- **Stratified**: 9 relevant + 6 irrelevant, matching the corpus split (63% relevant).
  Including irrelevant records is what makes precision and recall on the relevance
  decision meaningful — a sample of only relevant posts could not detect
  over-inclusion.
- **Spread across themes**: one record per theme first, then filled at random.
  Spread across themes so no single theme dominates the sample.
- Low-confidence records appear at their natural rate. The sample is not
  cherry-picked to flatter the model, and not stacked with hard cases either.

## How to fill it in

Open the CSV, read `title` and `description`, then complete the five `human_*`
columns. Leave a row blank to skip it — partial labelling is fine and is scored
on whatever exists.

| Column | Enter |
|---|---|
| `human_is_relevant` | `TRUE` or `FALSE` |
| `human_theme` | one theme from the list below |
| `human_journey_stage` | one stage from the list below |
| `human_feedback_type` | one type from the list below |
| `human_severity` | `1`–`5` |
| `notes` | optional — why you disagreed |

**Journey stages** (8, in lifecycle order — the order matters, stage 1 is the
earliest point a user can get stuck):

1. Action discovery & organization
2. Contextual entry, targeting & pre-fill
3. Form & input configuration
4. Validation, dependencies & conditional logic
5. Backend & invocation setup
6. Permissions & approvals
7. Testing, editing & publishing
8. Execution, monitoring & run control

**Themes** (11): Action discovery & organization · Context, targeting & pre-fill ·
Form structure, input types & controls · Dynamic & dependent inputs ·
Validation & error guidance · Backend & invocation configuration ·
Permissions, eligibility & action visibility · Approval workflows & governance ·
Testing, editing & drafts · Execution visibility, notifications & run control ·
Multi-step & orchestration

> The in-app **Themes & Journey Stages Guide** tab explains all of these in plain
> language, with examples for every category. It is the easiest way to label
> consistently — keep it open in another tab while you review.

**Feedback types:** Feature request · Usability friction · Bug ·
Documentation gap · Reliability issue

**Severity:** 5 blocking, no workaround · 4 major, expensive workaround ·
3 moderate friction · 2 minor · 1 nice to have

Full definitions are in [`TAXONOMY.md`](../../TAXONOMY.md).

## Then score it

```bash
python -m src.analysis.evaluate
```

Reports agreement per field, precision and recall on relevance, and a
disagreement table. Severity is reported separately (exact match, within-one, and
mean absolute error) because it is an ordinal judgment — a 3-vs-4 split is not
the same kind of error as a wrong theme.

## What this measures, and what it doesn't

With 15 records this is a **sanity check, not a statistically robust evaluation**.
It is enough to catch systematic problems — a taxonomy category nobody can apply
consistently, or relevance being drawn too wide — and not enough to state an
accuracy figure with confidence. Any result should be reported with the sample
size attached.

**At production scale** this becomes: a stratified sample per ingestion batch,
two independent reviewers with inter-annotator agreement (Cohen's kappa) to
separate *model* error from *taxonomy* ambiguity, disagreements feeding taxonomy
revisions, and a frozen gold set for regression-testing prompt changes.
