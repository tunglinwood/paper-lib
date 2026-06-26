#!/usr/bin/env python3
"""Inject the download-button module into all generated paper HTML files."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_DIR = ROOT / "archive" / "_unsorted" / "Library" / "01_curated" / "html"
SCRIPT_TAG = '<script type="module" src="/src/js/download-button.js?v=3"></script>'


def inject(html_path: Path) -> bool:
    """Inject the download-button script before </body> if not already present."""
    text = html_path.read_text(encoding="utf-8")
    if SCRIPT_TAG in text or "paper-download-btn" in text:
        return False

    # Try to insert right before </body>; fall back to appending before </html>.
    if "</body>" in text:
        new_text = text.replace("</body>", f"{SCRIPT_TAG}\n</body>", 1)
    elif "</html>" in text:
        new_text = text.replace("</html>", f"{SCRIPT_TAG}\n</html>", 1)
    else:
        new_text = text + "\n" + SCRIPT_TAG + "\n"

    html_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    if not HTML_DIR.is_dir():
        print(f"HTML directory not found: {HTML_DIR}", file=sys.stderr)
        return 1

    updated = 0
    skipped = 0
    for html_path in sorted(HTML_DIR.glob("*.html")):
        if inject(html_path):
            updated += 1
        else:
            skipped += 1

    print(f"Updated: {updated}, Skipped (already present): {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
