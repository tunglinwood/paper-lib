#!/usr/bin/env python3
"""
Inject Text Fragment support into pdf2htmlEX-generated HTML files.

This script adds JavaScript that enables the browser's native Text Fragments API
(#:~:text=...) to work with pdf2htmlEX's custom scroll container.

Usage:
    uv run python scripts/inject_text_fragment_support.py [--resume] [--workers N]
"""
import argparse
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
        const textFragmentStr = decodeURIComponent(hash.split(':~:text=')[1]);
        if (!textFragmentStr) return;
        console.log('[Text Fragment] Looking for:', textFragmentStr);
        const parsed = parseTextFragment(textFragmentStr);
        console.log('[Text Fragment] Parsed:', parsed);
        const range = findTextInDocument(parsed);
        if (!range) {
            console.warn('[Text Fragment] Text not found:', textFragmentStr);
            return;
        }
        scrollToRange(range);
        highlightRange(range);
    }
    function parseTextFragment(str) {
        // Syntax: [prefix-,]textStart[,textEnd][,-suffix]
        const parts = str.split(',');
        let prefix = null, textStart = null, textEnd = null, suffix = null;
        if (parts.length === 1) {
            textStart = parts[0];
        } else if (parts.length === 2) {
            if (parts[0].endsWith('-')) {
                prefix = parts[0].slice(0, -1);
                textStart = parts[1];
            } else if (parts[1].startsWith('-')) {
                textStart = parts[0];
                suffix = parts[1].slice(1);
            } else {
                textStart = parts[0];
                textEnd = parts[1];
            }
        } else if (parts.length === 3) {
            if (parts[0].endsWith('-')) {
                prefix = parts[0].slice(0, -1);
                if (parts[2].startsWith('-')) {
                    textStart = parts[1];
                    suffix = parts[2].slice(1);
                } else {
                    textStart = parts[1];
                    textEnd = parts[2];
                }
            } else {
                textStart = parts[0];
                textEnd = parts[1];
                if (parts[2].startsWith('-')) {
                    suffix = parts[2].slice(1);
                }
            }
        } else if (parts.length === 4) {
            prefix = parts[0].endsWith('-') ? parts[0].slice(0, -1) : parts[0];
            textStart = parts[1];
            textEnd = parts[2];
            suffix = parts[3].startsWith('-') ? parts[3].slice(1) : parts[3];
        }
        return { prefix, textStart, textEnd: textEnd || textStart, suffix };
    }
    function findTextInDocument(parsed) {
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
        const textLower = textContent.toLowerCase();
        const searchStart = parsed.textStart.toLowerCase();
        const searchEnd = parsed.textEnd.toLowerCase();
        let startIndex = textLower.indexOf(searchStart);
        while (startIndex !== -1) {
            if (parsed.prefix) {
                const prefixLower = parsed.prefix.toLowerCase();
                const beforeText = textLower.substring(Math.max(0, startIndex - 50), startIndex).trim();
                if (!beforeText.endsWith(prefixLower)) {
                    startIndex = textLower.indexOf(searchStart, startIndex + 1);
                    continue;
                }
            }
            let endIndex = -1;
            if (parsed.textEnd && parsed.textEnd !== parsed.textStart) {
                endIndex = textLower.indexOf(searchEnd, startIndex + searchStart.length);
                if (endIndex === -1) {
                    startIndex = textLower.indexOf(searchStart, startIndex + 1);
                    continue;
                }
                endIndex += searchEnd.length;
            } else {
                endIndex = startIndex + searchStart.length;
            }
            if (parsed.suffix) {
                const suffixLower = parsed.suffix.toLowerCase();
                const afterText = textLower.substring(endIndex, endIndex + 50).trim();
                if (!afterText.startsWith(suffixLower)) {
                    startIndex = textLower.indexOf(searchStart, startIndex + 1);
                    continue;
                }
            }
            break;
        }
        if (startIndex === -1) return null;
        let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
        for (let i = 0; i < textNodes.length; i++) {
            const {node, text, startIndex: nodeStart} = textNodes[i];
            const nodeEnd = nodeStart + text.length;
            if (!startNode && nodeStart <= startIndex && nodeEnd > startIndex) {
                startNode = node;
                startOffset = startIndex - nodeStart;
            }
            if (!endNode && nodeStart < endIndex && nodeEnd >= endIndex) {
                endNode = node;
                endOffset = endIndex - nodeStart;
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
