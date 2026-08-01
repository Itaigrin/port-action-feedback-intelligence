"""Generate the v3.0 TAXONOMY literal from the assignment workbook.

The workbook is the source of truth for the 63-to-30 consolidation, so the
taxonomy is generated from it rather than transcribed by hand: thirty
definitions and thirty boundary rules retyped by eye is thirty chances to
introduce a difference nobody would ever notice.

Run once to produce the block, paste into src/models/taxonomy.py, then delete
nothing -- the script stays so the next migration can be diffed against its
own input.

    python -m scripts.build_taxonomy_v3 > /tmp/taxonomy_v3.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WORKBOOK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\itaig\Downloads\Port_Feedback_Taxonomy_v3_Assignments.xlsx")

MAX_EXAMPLES = 2
# 185, not 150: at 150 the three records under "Server-side & API enforcement"
# were all just over the cap, and that subcategory generated with no example at
# all. A ceiling that silently empties a whole group is the wrong ceiling.
MAX_EXAMPLE_CHARS = 185


def _py(value: str, indent: int) -> str:
    """A Python string literal, wrapped so the generated file stays readable."""
    pad = " " * indent
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    if len(text) + indent + 2 <= 88:
        return f'"{text}"'
    words, lines, current = text.split(" "), [], ""
    for word in words:
        if current and len(current) + len(word) + 1 > 88 - indent - 3:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    body = f'\n{pad}'.join(f'"{ln} "' if i < len(lines) - 1 else f'"{ln}"'
                           for i, ln in enumerate(lines))
    return body


def main() -> None:
    nt = pd.read_excel(WORKBOOK, sheet_name="New Taxonomy")
    ra = pd.read_excel(WORKBOOK, sheet_name="Relevant Assignments")

    from src.models.taxonomy import TAXONOMY as OLD

    # Real quotes from records the workbook actually assigned to each
    # subcategory. Invented examples would teach the classifier a distinction
    # the data does not contain.
    examples: dict[str, list[str]] = {}
    for sub, group in ra.groupby("recommended_subcategory_v3"):
        picked = []
        for text in group["evidence_excerpt"].dropna():
            text = " ".join(str(text).split())
            if 25 <= len(text) <= MAX_EXAMPLE_CHARS and text not in picked:
                picked.append(text)
            if len(picked) == MAX_EXAMPLES:
                break
        examples[sub] = picked

    out = ["TAXONOMY: dict[str, dict] = {"]
    for category in dict.fromkeys(nt["Category"]):
        old = OLD[category]
        out.append(f'    {_py(category, 4)}: {{')
        out.append(f'        "plain": {_py(old["plain"], 18)},')
        out.append(f'        "default_stage": {_py(old["default_stage"], 25)},')
        confusable = ", ".join(f'"{c}"' for c in old["confusable"])
        out.append(f'        "confusable": [{confusable}],')
        out.append('        "subcategories": {')
        rows = nt[nt["Category"] == category]
        for _, r in rows.iterrows():
            sub = r["Recommended Subcategory v3"]
            out.append(f'            {_py(sub, 12)}: {{')
            out.append(f'                "plain": {_py(r["Definition"], 26)},')
            out.append('                "use_for": [')
            for former in str(r["Includes Former Subcategories"]).split(" | "):
                out.append(f'                    {_py(former.strip(), 20)},')
            out.append("                ],")
            out.append(f'                "avoid": {_py(r["Important Boundary"], 26)},')
            out.append('                "examples": [')
            for ex in examples.get(sub, []):
                out.append(f'                    {_py(chr(8220) + ex + chr(8221), 20)},')
            out.append("                ],")
            out.append("            },")
        out.append("        },")
        out.append("    },")
        out.append("")
    out.append("}")
    print("\n".join(out))


if __name__ == "__main__":
    main()
