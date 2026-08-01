"""Capture the README screenshots from a running dashboard.

Screenshots are the only part of the README that cannot be checked by a test,
so they are the part most likely to go stale after a UI change. Regenerating
them is one command rather than ten manual crops.

Start the app first, then:

    python -m streamlit run app.py --server.port 8504 --server.headless true
    python -m scripts.capture_screenshots
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
URL = "http://localhost:8504"

# (filename, tab index, anchor text to scroll to, extra height in px)
#
# Anchors are literal heading text from src/ui/render.py and app.py's
# render_guide(). Several headings were renamed or removed as the app
# evolved (the old dashboard "persona and secondary areas" chart no longer
# exists; the guide's "Worked examples" section was removed) -- when a
# heading changes, update the anchor here, not just the caption in README.md.
SHOTS = [
    ("01-executive-summary.png", 0, "Action Feedback Analyzer", 900),
    ("02-product-actions.png", 0, "Recommended product actions", 1100),
    ("03-categories.png", 0, "Matching feedback by category", 900),
    ("04-journey.png", 0, "Matching feedback by Journey stage", 900),
    ("05-where-users-struggle.png", 0, "Where users struggle most", 900),
    ("06-evidence.png", 0, "Feedback behind recommended actions", 800),
    ("07-guide-intro.png", 1, "Themes & Journey Stages Guide", 900),
    ("08-guide-categories.png", 1, "The 11 categories", 900),
    ("09-guide-stages.png", 1, "The 8 journey stages", 900),
    ("10-guide-severity-personas.png", 1, "Severity and personas", 900),
]

# Streamlit tabs are divs, not buttons with role=tab.
TAB = 'div[data-testid="stTab"]'


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=2)
        page.goto(URL, wait_until="networkidle", timeout=60_000)
        time.sleep(4)          # let plotly finish drawing

        current_tab = 0
        for filename, tab, anchor, height in SHOTS:
            if tab != current_tab:
                page.locator(TAB).nth(tab).click()
                time.sleep(3)
                current_tab = tab

            target = page.get_by_text(anchor, exact=False).first
            try:
                target.scroll_into_view_if_needed(timeout=10_000)
            except Exception:
                print(f"  ! anchor not found for {filename}: {anchor!r}")
                continue
            # Nudge up so the heading is not flush against the top edge.
            page.mouse.wheel(0, -80)
            time.sleep(1.5)

            page.set_viewport_size({"width": 1440, "height": height})
            time.sleep(1)
            page.screenshot(path=str(OUT / filename))
            page.set_viewport_size({"width": 1440, "height": 900})
            print(f"  wrote {filename}")

        # Full page last -- it changes the viewport most.
        page.locator(TAB).nth(0).click()
        time.sleep(3)
        page.screenshot(path=str(OUT / "00-full-page.png"), full_page=True)
        print("  wrote 00-full-page.png")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:                      # noqa: BLE001
        print(f"FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)
