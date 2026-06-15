#!/usr/bin/env python3
"""
Batch convert all PDF papers to HTML using pdf2htmlEX Docker image.
Each paper's HTML is stored in archive/_unsorted/Library/01_curated/html/{paper_id}.html
The html_path field in papers.db is updated accordingly.

Uses concurrent workers via ThreadPoolExecutor for fast conversion.

Usage:
    uv run python scripts/convert_papers_to_html.py           # Convert all
    uv run python scripts/convert_papers_to_html.py --resume  # Skip already-converted
    uv run python scripts/convert_papers_to_html.py --limit 3 # Convert first 3 only
    uv run python scripts/convert_papers_to_html.py --dry-run # Show what would be done
    uv run python scripts/convert_papers_to_html.py --workers 32  # Use 32 workers
"""
import argparse
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
PDF_BASE = ROOT / "archive" / "_unsorted" / "Library"
HTML_DIR = PDF_BASE / "01_curated" / "html"

DOCKER_IMAGE = "pdf2htmlex/pdf2htmlex:0.18.8.rc2-master-20200820-ubuntu-20.04-x86_64"

# Thread-safe progress counter
class Progress:
    def __init__(self):
        self._lock = threading.Lock()
        self.success = 0
        self.fail = 0
        self.skip = 0
        self.total = 0

    def snapshot(self):
        with self._lock:
            return self.success, self.fail, self.skip

    def report(self, index, total, title, status):
        s, f, sk = self.snapshot()
        print(f"[{index}/{total}] {status} {title}...  [{s} ok, {f} fail, {sk} skip]", file=sys.stderr)

progress = Progress()


def check_docker():
    """Verify Docker is available."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("ERROR: Docker is not working correctly.", file=sys.stderr)
            sys.exit(1)
        print(f"Docker available: {result.stdout.strip()}", file=sys.stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"ERROR: Docker not found: {e}", file=sys.stderr)
        sys.exit(1)


def get_papers_from_db():
    """Load all papers from SQLite."""
    conn = sqlite3.connect(str(ROOT / "papers.db"))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT paper_id, title, file_path, html_path FROM papers").fetchall()
    papers = [dict(r) for r in rows]
    conn.close()
    print(f"Loaded {len(papers)} papers from papers.db", file=sys.stderr)
    return papers


def convert_pdf_to_html(pdf_path: Path, output_path: Path) -> bool:
    """Run pdf2htmlEX via Docker to convert PDF to HTML with embedded resources.

    Uses a per-call temp directory to avoid file collisions when running
    multiple conversions in parallel (pdf2htmlEX writes CSS/fonts to the
    working directory).
    """
    if not pdf_path.exists():
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / pdf_path.name
        shutil.copy2(pdf_path, tmp_pdf)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{tmpdir}:/pdf",
            "-w", "/pdf",
            DOCKER_IMAGE,
            "--embed-css", "1",
            "--embed-font", "1",
            "--embed-image", "1",
            "--embed-javascript", "1",
            "--embed-outline", "1",
            "--zoom", "1.3",
            "--fit-width", "1024",
            pdf_path.name,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return False

            generated = Path(tmpdir) / pdf_path.name.replace(".pdf", ".html")
            if not generated.exists():
                return False

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(generated), str(output_path))

            return True

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False


def update_html_path_in_db(paper_id: str, html_path: str):
    """Update html_path for a paper in SQLite."""
    conn = sqlite3.connect(str(ROOT / "papers.db"))
    try:
        conn.execute("UPDATE papers SET html_path = ?, updated_at = datetime('now') WHERE paper_id = ?",
                     (html_path, paper_id))
        conn.commit()
    finally:
        conn.close()


def convert_paper(paper: dict, index: int, total: int) -> str:
    """Convert a single paper. Returns 'ok', 'fail', or 'skip'."""
    global progress

    paper_id = paper["paper_id"]
    title = paper.get("title", "Untitled")[:60]
    file_path = paper.get("file_path", "")

    if not file_path:
        progress.skip += 1
        progress.report(index, total, title, "SKIP (no file_path)")
        return "skip"

    pdf_path = PDF_BASE / file_path
    if not pdf_path.exists():
        progress.skip += 1
        progress.report(index, total, title, f"SKIP (PDF not found: {file_path})")
        return "skip"

    # Skip very large PDFs (>100MB)
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 100:
        progress.skip += 1
        progress.report(index, total, title, f"SKIP (too large: {file_size_mb:.0f}MB)")
        return "skip"

    output_path = HTML_DIR / f"{paper_id}.html"
    progress.report(index, total, title, "Converting...")

    if convert_pdf_to_html(pdf_path, output_path):
        relative_html_path = f"01_curated/html/{paper_id}.html"
        update_html_path_in_db(paper_id, relative_html_path)
        progress.success += 1
        return "ok"
    else:
        progress.fail += 1
        return "fail"


def main():
    parser = argparse.ArgumentParser(description="Batch convert PDFs to HTML via pdf2htmlEX Docker")
    parser.add_argument("--resume", action="store_true", help="Skip papers that already have html_path")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N papers")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--workers", type=int, default=16, help="Number of concurrent workers (default: 16)")
    args = parser.parse_args()

    check_docker()
    papers = get_papers_from_db()

    # Filter papers that already have html_path (resume mode)
    if args.resume:
        papers = [p for p in papers if not p.get("html_path")]
        print(f"Resume mode: {len(papers)} papers to convert", file=sys.stderr)

    # Apply limit
    if args.limit:
        papers = papers[:args.limit]
        print(f"Limit mode: processing {len(papers)} papers", file=sys.stderr)

    # Dry run
    if args.dry_run:
        print(f"\nDry run — would process {len(papers)} papers:", file=sys.stderr)
        for p in papers:
            print(f"  {p['paper_id'][:30]}... -> 01_curated/html/{p['paper_id']}.html", file=sys.stderr)
        return

    # Ensure HTML output directory exists
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    progress.total = len(papers)
    t0 = time.time()

    # Concurrent conversion
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for i, paper in enumerate(papers, 1):
            future = executor.submit(convert_paper, paper, i, progress.total)
            futures[future] = paper["paper_id"]

        for future in as_completed(futures):
            paper_id = futures[future]
            try:
                future.result()
            except Exception as e:
                progress.fail += 1
                print(f"Exception for {paper_id[:30]}...: {e}", file=sys.stderr)

    s, f, sk = progress.snapshot()
    total_elapsed = time.time() - t0
    print(f"\nDone in {total_elapsed/60:.1f}m! Success: {s}, Failed: {f}, Skipped: {sk}", file=sys.stderr)


if __name__ == "__main__":
    main()
