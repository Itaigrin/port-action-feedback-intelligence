"""Side-by-side visual-regression capture: mockup vs. the live Streamlit app.

Screenshots both at identical viewports so layout drift is visible rather than
argued about, and prints the measured geometry of the elements that matter for
parity.

Start the app first, then:

    python -m streamlit run app.py --server.port 8504 --server.headless true
    python -m scripts.capture_parity
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "parity"
MOCKUP = (ROOT / "docs" / "action_feedback_solution_mockup.html").as_uri()
APP = "http://localhost:8504"

VIEWPORTS = {"desktop": (1440, 1200), "mobile": (390, 844)}

# (label, mockup selector, app selector)
# No comparison-panel probe: that section was removed from the dashboard.
PROBES = [
    ("topbar", ".topbar", ".afi-topbar"),
    ("sidebar", ".sidebar .panel", ".st-key-afi_rail"),
    ("hero", ".hero", ".afi-hero"),
    ("kpi-row", ".kpis", ".afi-kpis"),
    ("kpi-card", ".kpi", ".afi-kpi"),
    ("actions-panel", "#actionsSection", ".afi-actions"),
    ("charts-panel", "#featureAreasSection", ".st-key-afi_charts"),
    ("feedback-section", "#evidenceSection", ".st-key-afi_feedback"),
]


def measure(page, selectors: list[str]) -> dict:
    out: dict[str, dict] = {}
    for label, selector in selectors:
        try:
            box = page.locator(selector).first.bounding_box(timeout=2500)
        except Exception:
            box = None
        out[label] = (
            {k: round(v) for k, v in box.items()} if box else {"missing": True}
        )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, (w, h) in VIEWPORTS.items():
            for side, url, index in (("mockup", MOCKUP, 0), ("app", APP, 1)):
                page = browser.new_page(viewport={"width": w, "height": h},
                                        device_scale_factor=2)
                page.goto(url, wait_until="networkidle", timeout=60_000)
                time.sleep(3.5 if side == "app" else 1.0)

                page.screenshot(path=str(OUT / f"{side}-{name}.png"))
                page.screenshot(path=str(OUT / f"{side}-{name}-full.png"),
                                full_page=True)
                report[f"{side}-{name}"] = measure(
                    page, [(probe[0], probe[1 + index]) for probe in PROBES]
                )
                print(f"  wrote {side}-{name}.png")
                page.close()
        browser.close()

    (OUT / "geometry.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print("\nGeometry (width x height @ x,y)")
    for name in VIEWPORTS:
        print(f"\n  --- {name} ---")
        print(f"  {'element':20s} {'mockup':>22s} {'app':>22s}")
        for label, *_ in PROBES:
            m = report[f"mockup-{name}"].get(label, {})
            a = report[f"app-{name}"].get(label, {})

            def fmt(b: dict) -> str:
                if b.get("missing"):
                    return "MISSING"
                return f"{b['width']}x{b['height']} @{b['x']},{b['y']}"

            print(f"  {label:20s} {fmt(m):>22s} {fmt(a):>22s}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:                      # noqa: BLE001
        print(f"FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)
