# Text Fragment Support for Paper HTML Files

## Overview

This feature enables **text selection and sharing** for pdf2htmlEX-generated HTML files. Users can now:

1. Select text in a paper
2. Copy the URL (which includes a `#:~:text=...` fragment)
3. Share the link with others
4. Clicking the link scrolls to and highlights the selected text — **on any page**

## How It Works

Modern browsers support the [Text Fragments API](https://wicg.github.io/scroll-to-text-fragment/), which allows URLs to include text directives like:

```
https://example.com/paper.html#:~:text=selected%20text%20here
```

When someone opens this URL, the browser automatically:
- Finds the specified text
- Scrolls to it
- Highlights it with a yellow background

### The Problem

pdf2htmlEX uses a **custom scroll container** (`#page-container` with `overflow: auto`), but the browser's Text Fragments API only scrolls the **main window**. This means:
- ✅ Text on page 1 works (visible in viewport)
- ❌ Text on pages 2+ doesn't work (inside custom scroll container)

### The Solution

We inject custom JavaScript into each HTML file that:
1. Detects Text Fragment URLs (`#:~:text=...`)
2. Searches for the text across **all pages** (not just visible ones)
3. Scrolls the `#page-container` to bring the text into view
4. Highlights the text with a yellow `<mark>` element (removes after 5 seconds)

## Implementation

### Files

- **`deploy/text-fragment-support.js`** — Standalone JavaScript module
- **`scripts/inject_text_fragment_support.py`** — Injects the script into existing HTML files

### Inject into Existing HTML Files

```bash
# Process all HTML files (skip already-injected ones)
uv run python scripts/inject_text_fragment_support.py --resume

# Results:
#   Success: 352 files
#   Skipped: 3 files (already injected)
#   Failed: 0 files
```

### Manual Injection

To add to a single HTML file:

```python
from pathlib import Path
from scripts.inject_text_fragment_support import inject_into_html

html_file = Path("archive/_unsorted/Library/01_curated/html/paper.html")
inject_into_html(html_file)
```

## Usage Examples

### Example 1: Share Text from Page 3

1. Open a paper: `http://localhost:9000/papers/sha256_xxx.html`
2. Navigate to page 3
3. Select some text (e.g., "concentratio")
4. Copy the URL — browser adds `#:~:text=concentratio`
5. Share the link: `http://localhost:9000/papers/sha256_xxx.html#:~:text=concentratio`
6. Recipient clicks the link → page scrolls to page 3, text is highlighted

### Example 2: Direct Link to Specific Text

Construct a URL manually:

```
http://localhost:9000/papers/sha256_xxx.html#:~:text=glucokinase%20activity
```

When opened, the browser will:
- Search for "glucokinase activity" across all pages
- Scroll to the first match
- Highlight it in yellow for 5 seconds

## Browser Compatibility

The Text Fragments API is supported in:
- ✅ Chrome 80+
- ✅ Edge 80+
- ✅ Safari 15.4+
- 🔄 Firefox (in development)

For browsers without native support, our custom JavaScript still works — it just won't have the browser's native highlighting.

## Technical Details

### JavaScript Injection

The script is injected before `</body>` in each HTML file:

```html
<script>
// Text Fragment support for pdf2htmlEX
(function() {
    // ... (see deploy/text-fragment-support.js for full code)
})();
</script>
```

### How It Finds Text

1. Uses `TreeWalker` to collect all text nodes in `#page-container`
2. Concatenates text content with position tracking
3. Searches for the target text (case-insensitive)
4. Creates a `Range` object spanning the match

### How It Scrolls

1. Gets the bounding rect of the matched text
2. Calculates scroll position to center the text in the viewport
3. Uses `container.scrollTo()` with smooth animation

### How It Highlights

1. Wraps the matched text in a `<mark>` element
2. Styles it with yellow background
3. Removes the highlight after 5 seconds (restores original DOM)

## Limitations

- **Long text**: Very long selections (>100 words) may not highlight correctly
- **Dynamic content**: If pages are lazy-loaded, text might not be found initially
- **Cross-page selections**: Text spanning multiple pages may not highlight correctly

## Future Enhancements

Potential improvements:
- [ ] Support for text prefix/suffix in Text Fragments (`prefix-,text,suffix`)
- [ ] Persistent highlights (save to localStorage)
- [ ] Multiple highlights per page
- [ ] Highlight color customization
- [ ] Export highlights as annotations

## Testing

Test with a multi-page paper:

```bash
# Open in browser
http://localhost:9000/papers/sha256_01db7e8ca3ba3bbbd16765eba950300511c92e9bc2e090d990e297c5928132a2.html#:~:text=concentratio
```

Expected behavior:
1. Page loads
2. Automatically scrolls to page 3
3. "concentratio" is highlighted in yellow
4. Highlight fades after 5 seconds

## Related

- [Text Fragments API Spec](https://wicg.github.io/scroll-to-text-fragment/)
- [MDN: URL Fragment Text Directive](https://developer.mozilla.org/en-US/docs/Web/Text_fragments)
- [pdf2htmlEX](https://github.com/pdf2htmlEX/pdf2htmlEX)
