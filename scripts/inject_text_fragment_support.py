#!/usr/bin/env python3
"""
Inject Text Fragment support into pdf2htmlEX-generated HTML files.

This script adds JavaScript that enables the browser's native Text Fragments API
(#:~:text=...) to work with pdf2htmlEX's custom scroll container.

Usage:
    uv run python scripts/inject_text_fragment_support.py [--resume] [--workers N]
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "archive" / "_unsorted" / "Library" / "01_curated" / "html"

# The JavaScript to inject
TEXT_FRAGMENT_JS = """
<script>
// Text Fragment support for pdf2htmlEX
(function() {
    'use strict';
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTextFragmentSupport);
    } else {
        initTextFragmentSupport();
    }
    function initTextFragmentSupport() {
        const hash = window.location.hash;
        if (!hash.includes(':~:text=')) return;
        const textFragment = decodeURIComponent(hash.split(':~:text=')[1]);
        if (!textFragment) return;
        console.log('[Text Fragment] Looking for:', textFragment);
        const range = findTextInDocument(textFragment);
        if (!range) {
            console.warn('[Text Fragment] Text not found:', textFragment);
            return;
        }
        scrollToRange(range);
        highlightRange(range);
    }
    function findTextInDocument(searchText) {
        const treeWalker = document.createTreeWalker(
            document.querySelector('#page-container') || document.body,
            NodeFilter.SHOW_TEXT, null, false
        );
        let node, textContent = '', textNodes = [];
        while (node = treeWalker.nextNode()) {
            const text = node.textContent.trim();
            if (text) {
                textNodes.push({node, text, startIndex: textContent.length});
                textContent += text + ' ';
            }
        }
        const searchLower = searchText.toLowerCase();
        const textLower = textContent.toLowerCase();
        const matchIndex = textLower.indexOf(searchLower);
        if (matchIndex === -1) return null;
        const matchEnd = matchIndex + searchText.length;
        let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
        for (let i = 0; i < textNodes.length; i++) {
            const {node, text, startIndex} = textNodes[i];
            const endIndex = startIndex + text.length;
            if (!startNode && startIndex <= matchIndex && endIndex > matchIndex) {
                startNode = node;
                startOffset = matchIndex - startIndex;
            }
            if (!endNode && startIndex < matchEnd && endIndex >= matchEnd) {
                endNode = node;
                endOffset = matchEnd - startIndex;
                break;
            }
        }
        if (!startNode || !endNode) return null;
        const range = document.createRange();
        range.setStart(startNode, startOffset);
        range.setEnd(endNode, endOffset);
        return range;
    }
    function scrollToRange(range) {
        const rect = range.getBoundingClientRect();
        const container = document.querySelector('#page-container');
        if (!container) {
            const element = range.commonAncestorContainer.nodeType === Node.TEXT_NODE
                ? range.commonAncestorContainer.parentElement
                : range.commonAncestorContainer;
            element.scrollIntoView({behavior: 'smooth', block: 'center'});
            return;
        }
        const containerRect = container.getBoundingClientRect();
        const scrollTop = container.scrollTop + rect.top - containerRect.top - containerRect.height / 2 + rect.height / 2;
        const scrollLeft = container.scrollLeft + rect.left - containerRect.left - containerRect.width / 2 + rect.width / 2;
        container.scrollTo({top: scrollTop, left: scrollLeft, behavior: 'smooth'});
    }
    function highlightRange(range) {
        const highlight = document.createElement('mark');
        highlight.style.cssText = 'background-color: yellow; color: black; padding: 2px 0;';
        try {
            highlight.appendChild(range.extractContents());
            range.insertNode(highlight);
            setTimeout(() => {
                const parent = highlight.parentNode;
                while (highlight.firstChild) parent.insertBefore(highlight.firstChild, highlight);
                parent.removeChild(highlight);
            }, 5000);
        } catch (e) {
            console.error('[Text Fragment] Failed to highlight:', e);
        }
    }
})();
</script>
"""


def inject_into_html(html_path: Path) -> bool:
    """Inject Text Fragment support into an HTML file."""
    try:
        content = html_path.read_text(encoding='utf-8', errors='replace')

        # Check if already injected
        if 'Text Fragment support for pdf2htmlEX' in content:
            return False

        # Find the closing </body> tag and inject before it
        if '</body>' in content:
            content = content.replace('</body>', f'{TEXT_FRAGMENT_JS}\n</body>')
        else:
            # Fallback: inject before </html>
            content = content.replace('</html>', f'{TEXT_FRAGMENT_JS}\n</html>')

        html_path.write_text(content, encoding='utf-8')
        return True

    except Exception as e:
        print(f"ERROR: Failed to process {html_path}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inject Text Fragment support into pdf2htmlEX HTML files"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip files that already have Text Fragment support",
    )
    args = parser.parse_args()

    if not HTML_DIR.exists():
        print(f"ERROR: HTML directory not found: {HTML_DIR}", file=sys.stderr)
        sys.exit(1)

    html_files = sorted(HTML_DIR.glob("*.html"))
    if not html_files:
        print("ERROR: No HTML files found", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(html_files)} HTML files", file=sys.stderr)

    success = 0
    skipped = 0
    failed = 0

    for i, html_file in enumerate(html_files, 1):
        # Check if already has Text Fragment support
        content = html_file.read_text(encoding='utf-8', errors='replace')
        if 'Text Fragment support for pdf2htmlEX' in content:
            if args.resume:
                skipped += 1
                continue

        print(f"[{i}/{len(html_files)}] Processing {html_file.name}...", file=sys.stderr)

        if inject_into_html(html_file):
            success += 1
        else:
            failed += 1

    print(f"\nDone!", file=sys.stderr)
    print(f"  Success: {success}", file=sys.stderr)
    print(f"  Skipped: {skipped}", file=sys.stderr)
    print(f"  Failed: {failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
