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
        const textFragment = decodeURIComponent(hash.split(':~:text=')[1]);
        if (!textFragment) {
            return;
        }

        console.log('[Text Fragment] Looking for:', textFragment);

        // Find the text in the document
        const range = findTextInDocument(textFragment);
        if (!range) {
            console.warn('[Text Fragment] Text not found:', textFragment);
            return;
        }

        // Scroll to the text
        scrollToRange(range);

        // Highlight the text
        highlightRange(range);
    }

    /**
     * Find text in the document and return a Range object
     */
    function findTextInDocument(searchText) {
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

        // Search for the text
        const searchLower = searchText.toLowerCase();
        const textLower = textContent.toLowerCase();
        const matchIndex = textLower.indexOf(searchLower);

        if (matchIndex === -1) {
            return null;
        }

        // Find which text node contains the start of the match
        let matchEnd = matchIndex + searchText.length;
        let startNode = null;
        let startOffset = 0;
        let endNode = null;
        let endOffset = 0;

        for (let i = 0; i < textNodes.length; i++) {
            const { node, text, startIndex } = textNodes[i];
            const endIndex = startIndex + text.length;

            // Check if this node contains the start of the match
            if (!startNode && startIndex <= matchIndex && endIndex > matchIndex) {
                startNode = node;
                startOffset = matchIndex - startIndex;
            }

            // Check if this node contains the end of the match
            if (!endNode && startIndex < matchEnd && endIndex >= matchEnd) {
                endNode = node;
                endOffset = matchEnd - startIndex;
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
