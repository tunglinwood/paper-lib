/**
 * Text Fragment support for pdf2htmlEX-generated HTML files
 *
 * This script enables the browser's native Text Fragments API (#:~:text=...)
 * to work with pdf2htmlEX's custom scroll container.
 *
 * Usage: Inject this script into pdf2htmlEX HTML files, or serve it alongside
 * and reference it in the HTML.
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTextFragmentSupport);
    } else {
        initTextFragmentSupport();
    }

    function initTextFragmentSupport() {
        const hash = window.location.hash;

        // Check if URL contains a Text Fragment directive
        if (!hash.includes(':~:text=')) {
            return;
        }

        // Extract the text fragment
        const textFragmentStr = decodeURIComponent(hash.split(':~:text=')[1]);
        if (!textFragmentStr) {
            return;
        }

        console.log('[Text Fragment] Looking for:', textFragmentStr);

        // Parse the text fragment syntax
        const parsed = parseTextFragment(textFragmentStr);
        console.log('[Text Fragment] Parsed:', parsed);

        // Find the text in the document
        const range = findTextInDocument(parsed);
        if (!range) {
            console.warn('[Text Fragment] Text not found:', textFragmentStr);
            return;
        }

        // Scroll to the text
        scrollToRange(range);

        // Highlight the text
        highlightRange(range);
    }

    /**
     * Parse Text Fragment syntax: [prefix-,]textStart[,textEnd][,-suffix]
     */
    function parseTextFragment(str) {
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

    /**
     * Find text in the document and return a Range object
     * Uses parsed text fragment with prefix, textStart, textEnd, suffix
     */
    function findTextInDocument(parsed) {
        const treeWalker = document.createTreeWalker(
            document.querySelector('#page-container') || document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        let node;
        let textContent = '';
        const textNodes = [];

        // Collect all text nodes
        while (node = treeWalker.nextNode()) {
            const text = node.textContent.trim();
            if (text) {
                textNodes.push({
                    node: node,
                    text: text,
                    startIndex: textContent.length
                });
                textContent += text + ' ';
            }
        }

        // Search for textStart
        const textLower = textContent.toLowerCase();
        const searchStart = parsed.textStart.toLowerCase();
        const searchEnd = parsed.textEnd.toLowerCase();

        let startIndex = textLower.indexOf(searchStart);
        while (startIndex !== -1) {
            // Check prefix if specified
            if (parsed.prefix) {
                const prefixLower = parsed.prefix.toLowerCase();
                const beforeText = textLower.substring(Math.max(0, startIndex - 50), startIndex).trim();
                if (!beforeText.endsWith(prefixLower)) {
                    startIndex = textLower.indexOf(searchStart, startIndex + 1);
                    continue;
                }
            }

            // Find textEnd
            let endIndex = -1;
            if (parsed.textEnd && parsed.textEnd !== parsed.textStart) {
                endIndex = textLower.indexOf(searchEnd, startIndex + searchStart.length);
                if (endIndex === -1) {
                    startIndex = textLower.indexOf(searchStart, startIndex + 1);
                    continue;
                }
                endIndex += searchEnd.length;
            } else {
                // textEnd is same as textStart or not specified
                endIndex = startIndex + searchStart.length;
            }

            // Check suffix if specified
            if (parsed.suffix) {
                const suffixLower = parsed.suffix.toLowerCase();
                const afterText = textLower.substring(endIndex, endIndex + 50).trim();
                if (!afterText.startsWith(suffixLower)) {
                    startIndex = textLower.indexOf(searchStart, startIndex + 1);
                    continue;
                }
            }

            // All checks passed
            break;
        }

        if (startIndex === -1) {
            return null;
        }

        // Find which text nodes contain the start and end of the match
        let startNode = null;
        let startOffset = 0;
        let endNode = null;
        let endOffset = 0;

        for (let i = 0; i < textNodes.length; i++) {
            const { node, text, startIndex: nodeStart } = textNodes[i];
            const nodeEnd = nodeStart + text.length;

            // Check if this node contains the start of the match
            if (!startNode && nodeStart <= startIndex && nodeEnd > startIndex) {
                startNode = node;
                startOffset = startIndex - nodeStart;
            }

            // Check if this node contains the end of the match
            if (!endNode && nodeStart < endIndex && nodeEnd >= endIndex) {
                endNode = node;
                endOffset = endIndex - nodeStart;
                break;
            }
        }

        if (!startNode || !endNode) {
            return null;
        }

        // Create a Range object
        const range = document.createRange();
        range.setStart(startNode, startOffset);
        range.setEnd(endNode, endOffset);

        return range;
    }

    /**
     * Scroll the page-container to bring the range into view
     */
    function scrollToRange(range) {
        const rect = range.getBoundingClientRect();
        const container = document.querySelector('#page-container');

        if (!container) {
            // Fallback: scroll the element into view
            const element = range.commonAncestorContainer.nodeType === Node.TEXT_NODE
                ? range.commonAncestorContainer.parentElement
                : range.commonAncestorContainer;
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }

        const containerRect = container.getBoundingClientRect();

        // Calculate scroll position
        const scrollTop = container.scrollTop + rect.top - containerRect.top - containerRect.height / 2 + rect.height / 2;
        const scrollLeft = container.scrollLeft + rect.left - containerRect.left - containerRect.width / 2 + rect.width / 2;

        // Scroll with smooth animation
        container.scrollTo({
            top: scrollTop,
            left: scrollLeft,
            behavior: 'smooth'
        });
    }

    /**
     * Highlight the range with a visual indicator
     */
    function highlightRange(range) {
        // Create a highlight span
        const highlight = document.createElement('mark');
        highlight.style.cssText = 'background-color: yellow; color: black; padding: 2px 0;';

        // Wrap the range content
        try {
            highlight.appendChild(range.extractContents());
            range.insertNode(highlight);

            // Remove highlight after 5 seconds
            setTimeout(() => {
                const parent = highlight.parentNode;
                while (highlight.firstChild) {
                    parent.insertBefore(highlight.firstChild, highlight);
                }
                parent.removeChild(highlight);
            }, 5000);
        } catch (e) {
            console.error('[Text Fragment] Failed to highlight:', e);
        }
    }
})();
