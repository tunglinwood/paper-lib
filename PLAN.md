# Paper Library: Monolith to Structured Frontend - Implementation Plan

## 1. Requirements Restatement

The current Paper Library is a single-page application contained entirely in `/opt/fastgpt/4.9.8/static-assets/index.html` (694 lines, ~35KB). It embeds all CSS and JavaScript inline with zero build step. The application provides:

- **Paper browsing**: Searchable, filterable list of 320 academic papers loaded from `/static-assets/index.jsonl` (JSONL format, one JSON object per line)
- **Client-side search**: Full-text filter across title, authors, venue, tags, DOI, and notes
- **Sidebar filters**: Year pills, source checkboxes, and topic tags
- **Trending display**: Time-windowed rankings (7d/30d/all) fetched from `/static-assets/api/rankings`
- **Paper detail modal**: Metadata display, related papers, PDF preview toggle
- **Bulk actions**: Select multiple papers and export BibTeX citations
- **View tracking**: POST to `/static-assets/api/track-view` (handled by `server.cjs` on port 8080)
- **Pagination**: 20 items per page with page controls
- **Sorting**: By relevance, year, or title

**Serving context**: The HTML file is served two ways:
1. Via FastGPT on port 3000 at `/static-assets/paper-lib/index.html` (static file serving)
2. Via nginx on port 443 at `/static-assets/index.html` (alias directive), with `/static-assets/api/` proxied to server.cjs on port 8080
3. Directly via server.cjs on port 8080 (which uses `location.port === '3000'` detection to choose `API_BASE`)

**Current data schema** (per paper in index.jsonl):
`paper_id`, `title`, `authors`, `year`, `venue`, `doi`, `arxiv_id`, `pmid`, `pmcid`, `file_path`, `file_hash_sha256`, `file_size_bytes`, `file_ext`, `added_at`, `tags`, `notes`, `status`, `source`, `kind`, `source_path`, `display_path`

## 2. Proposed File Structure

```
paper-lib/
├── server.cjs                          # Backend (unchanged, serves static + API)
├── ecosystem.config.cjs                # PM2 config (unchanged)
│
├── index.html                          # HTML skeleton with <link> and <script type="module">
│
├── src/                                # Source files (development)
│   ├── css/
│   │   ├── base.css                    # Reset, typography, body, CSS custom properties
│   │   ├── layout.css                  # Grid, container, responsive breakpoints
│   │   ├── header.css                  # Header gradient, search bar
│   │   ├── sidebar.css                 # Sidebar, stat cards, filter groups
│   │   ├── trending.css                # Trending bar, tabs, list items
│   │   ├── cards.css                   # Paper cards, tags, actions
│   │   ├── pagination.css              # Pagination controls
│   │   ├── modal.css                   # Modal overlay, content, PDF viewer
│   │   └── loading.css                 # Spinner, loading states
│   │
│   └── js/
│       ├── main.js                     # Entry point, init(), event listeners
│       ├── api.js                      # API layer: fetch wrappers for all endpoints
│       ├── data.js                     # Data layer: load, parse, cache index.jsonl
│       ├── state.js                    # Application state: filters, selection, pagination
│       ├── search.js                   # Search logic: searchPapersLocal, topic extraction
│       ├── render/
│       │   ├── papers.js               # Render paper cards, paper list
│       │   ├── pagination.js           # Render pagination controls
│       │   ├── filters.js              # Render year pills, source filters, topic tags
│       │   ├── trending.js             # Render trending list
│       │   ├── modal.js                # Render paper detail modal
│       │   └── stats.js                # Render stat cards
│       ├── actions/
│       │   ├── export.js               # BibTeX generation, bulk export, blob download
│       │   ├── pdf.js                  # PDF preview, download
│       │   └── tracking.js             # View tracking, trending refresh
│       └── utils/
│           ├── escape.js               # HTML escaping utility
│           └── dom.js                  # DOM helper utilities
│
├── dist/                               # Built output (served to users, if build added later)
│   ├── index.html                      # Assembled production HTML file
│   ├── css/
│   │   └── paper-lib.css               # Concatenated + minified CSS
│   └── js/
│       └── paper-lib.js                # Bundled + minified JS
│
├── .gitignore                          # Ignores dist/
├── PLAN.md                             # This file
└── CLAUDE.md                           # Updated with new structure
```

## 3. JavaScript Split Strategy

### 3.1 Module Breakdown

| Module | Responsibility | Current lines (approx) |
|--------|---------------|----------------------|
| `data.js` | Load and parse `index.jsonl`, provide paper array access | ~10 (loadPapersData) |
| `api.js` | All `fetch()` calls: track-view, rankings, data loading | ~30 (trackView, loadTrending) |
| `state.js` | `allPapers`, `filteredPapers`, `selectedYears`, `currentPage`, `selectedPapers`, `currentPaper`, `currentTrendingWindow` | ~20 (all global state declarations) |
| `search.js` | `searchPapersLocal()`, `extractTopics()`, `searchByTopic()` | ~30 (searchPapersLocal, extractTopics) |
| `render/papers.js` | `renderPapers()` - card HTML generation | ~40 (paper card template) |
| `render/pagination.js` | `renderPaginationControls()`, `goPage()` | ~40 (pagination logic) |
| `render/filters.js` | `populateYearPills()`, `populateFilters()`, `toggleYear()`, `updateYearPillUI()` | ~30 (filter rendering) |
| `render/trending.js` | Trending list rendering from API response | ~20 (part of loadTrending) |
| `render/modal.js` | `showPaper()`, `closeModal()`, `togglePreview()`, related papers | ~60 (showPaper, modal logic) |
| `render/stats.js` | `loadStats()` - populate stats, year/source/topic filters | ~30 (loadStats) |
| `actions/export.js` | `generateBibtex()`, `exportCitation()`, `exportSelected()`, `downloadBlob()` | ~40 (export functions) |
| `actions/pdf.js` | `downloadPaper()` | ~10 (downloadPaper) |
| `actions/tracking.js` | `trackView()`, `refreshTrending()`, trending debouncing | ~20 (trackView, refreshTrending) |
| `utils/escape.js` | `escapeHtml()` | ~5 (escapeHtml) |
| `main.js` | `init()`, `searchPapers()`, `applyFilters()`, `sortPapers()`, event listeners | ~40 (init, glue logic, listeners) |

### 3.2 Module Dependency Graph

```
main.js
  -> state.js (imports shared state)
  -> data.js (loadPapers)
  -> api.js (trackView, loadTrending)
  -> search.js (searchPapersLocal, extractTopics)
  -> render/stats.js (loadStats)
  -> render/papers.js (renderPapers)
  -> render/pagination.js (renderPaginationControls, goPage)
  -> render/filters.js (populateYearPills, toggleYear, applyFilters)
  -> render/trending.js (loadTrending + render)
  -> render/modal.js (showPaper, closeModal, togglePreview)
  -> actions/export.js (exportCitation, exportSelected)
  -> actions/pdf.js (downloadPaper)
  -> actions/tracking.js (trackView, refreshTrending)
  -> utils/escape.js (escapeHtml)
```

### 3.3 ES Module Approach (No Build Step)

Each `.js` file uses ES module syntax:

```js
// src/js/state.js
export const state = {
  allPapers: [],
  filteredPapers: [],
  selectedYears: new Set(),
  currentPage: 1,
  selectedPapers: new Set(),
  currentPaper: null,
  currentTrendingWindow: '7',
};
export const PAGE_SIZE = 20;
```

```js
// src/js/api.js
export function getApiBase() {
  return location.port === '3000'
    ? `//${location.hostname}:8080`
    : '/static-assets';
}

export async function trackView(paperId, type = 'preview') {
  fetch(`${getApiBase()}/api/track-view`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_id: paperId, type }),
  }).catch(() => {});
}

export async function fetchRankings(windowDays) {
  const resp = await fetch(`${getApiBase()}/api/rankings?window=${windowDays}`);
  return resp.json();
}
```

```js
// src/js/main.js (entry point)
import { state, PAGE_SIZE } from './state.js';
import { loadPapersData } from './data.js';
import { loadStats } from './render/stats.js';
// ... more imports

// Event listeners
document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') searchPapers();
});

// Initialize
init().then(() => loadTrending('7'));
```

The HTML entry point loads the module:
```html
<script type="module" src="./src/js/main.js"></script>
```

### 3.4 Cross-Cutting Concerns

- **`API_BASE` detection**: Centralize in `api.js` as a single `getApiBase()` function. All API calls import from there.
- **`escapeHtml`**: Pure utility, exported from `utils/escape.js`, imported by any render module that generates HTML.
- **Global state**: Consolidate all globals into a single `state` object in `state.js`. This eliminates the implicit global scope that currently couples everything together.
- **Debounced trending refresh**: Keep in `actions/tracking.js` with the `trendingRefreshTimer` variable scoped locally.

## 4. CSS Split Strategy

### 4.1 File Breakdown

| File | Content | Lines (approx) |
|------|---------|---------------|
| `css/base.css` | Universal reset, body styles, CSS custom properties (colors, spacing), `@keyframes spin` | ~8 |
| `css/layout.css` | `.container` grid, responsive `@media` breakpoint, `.papers-header` flex | ~4 |
| `css/header.css` | `.header` gradient/title/subtitle, `.search-container`, `.search-box`, `.search-input`, `.search-btn` | ~10 |
| `css/sidebar.css` | `.sidebar`, `.stats`, `.stat-card`, `.filter-group`, `.filter-option`, `.topic-tag` | ~15 |
| `css/trending.css` | `.trending-bar`, `.trending-header`, `.trending-tabs`, `.trending-tab` states, `.trending-list`, `.trending-item`, `.trending-rank` (gold/silver/bronze), `.trending-title`, `.trending-count`, `.trending-empty` (both regular and bar variants) | ~35 |
| `css/cards.css` | `.paper-card`, `.paper-title`, `.paper-authors`, `.paper-meta`, `.paper-tags`, `.tag`, `.tag.doi`, `.paper-actions`, `.action-btn`, `.action-btn.selected` | ~20 |
| `css/pagination.css` | `.pagination`, `.page-btn` (all states), `.page-info` | ~8 |
| `css/modal.css` | `.modal` (hidden/active), `.modal-content`, `.modal-header`, `.modal-close`, `.modal-body`, `.pdf-preview` | ~12 |
| `css/loading.css` | `.loading`, `.spinner`, `@keyframes spin` (if not in base) | ~5 |

### 4.2 CSS Custom Properties (Recommended Enhancement)

Extract magic values into CSS custom properties at the top of `base.css`:

```css
:root {
  --color-primary: #667eea;
  --color-primary-dark: #5568d3;
  --color-secondary: #764ba2;
  --color-text: #333;
  --color-text-muted: #666;
  --color-text-light: #888;
  --color-text-placeholder: #999;
  --color-bg: #f5f7fa;
  --color-bg-white: #ffffff;
  --color-bg-subtle: #f0f0f0;
  --color-border: #ddd;
  --color-border-light: #f0f0f0;
  --color-border-lighter: #f9f9f9;
  --color-doi-bg: #e8f4fd;
  --color-doi-text: #0066cc;
  --color-gold: #f59e0b;
  --color-silver: #94a3b8;
  --color-bronze: #d97706;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-pill: 20px;
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.1);
  --shadow-search: 0 4px 20px rgba(0,0,0,0.1);
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --max-width: 1200px;
  --sidebar-width: 280px;
  --transition-fast: 0.2s;
}
```

This makes the purple/gradient theme consistent and easy to re-theme.

### 4.3 CSS Loading Order in HTML

```html
<link rel="stylesheet" href="./src/css/base.css">
<link rel="stylesheet" href="./src/css/layout.css">
<link rel="stylesheet" href="./src/css/header.css">
<link rel="stylesheet" href="./src/css/sidebar.css">
<link rel="stylesheet" href="./src/css/trending.css">
<link rel="stylesheet" href="./src/css/cards.css">
<link rel="stylesheet" href="./src/css/pagination.css">
<link rel="stylesheet" href="./src/css/modal.css">
<link rel="stylesheet" href="./src/css/loading.css">
```

## 5. Minimal HTML Skeleton

The new `index.html` strips out all inline CSS and JS. Key structural changes:

1. Remove all `onclick="..."` inline handlers -- replaced by `addEventListener` in JS modules
2. Remove the `<style>` block entirely
3. Replace the `<script>` block with a single `<script type="module">` entry point
4. Add `id` attributes to buttons that previously used `onclick` (e.g., `searchBtn`, `exportBtn`, `clearBtn`, `modalCloseBtn`, `downloadBtn`, `exportCitationBtn`, `togglePreviewBtn`)
5. Add `data-action` attributes to dynamically-generated buttons for event delegation

## 6. Risks and Tradeoffs

### 6.1 ES Modules Without Build Step

**Risk: CORS on `file://` protocol**
- ES modules do not work when opening HTML files directly via `file://`. The app currently works this way for local development.
- **Mitigation**: Require `server.cjs` (or any HTTP server) for local development. This is already the documented workflow (`node server.cjs`).

**Risk: Browser compatibility**
- ES modules are supported in all modern browsers (Chrome 61+, Firefox 60+, Safari 11+, Edge 16+). The target audience (research team) uses modern browsers.
- **Mitigation**: No concern for this project.

**Risk: Multiple network requests**
- Splitting into ~20 JS files means ~20 HTTP requests on initial load (unless cached). The current single file is one request.
- **Mitigation**: All files are static and cacheable. After first load, browser cache eliminates requests. For production, consider a build step to concatenate (see 6.4).

### 6.2 Inline `onclick` Removal

**Risk: Event delegation complexity**
- The current code uses `onclick` on dynamically generated elements (paper cards, trending items, year pills). Moving to `addEventListener` requires event delegation on parent containers.
- **Mitigation**: Use event delegation on `#papersList`, `#trendingList`, and `#yearFilters`. Attach `data-action` attributes to interactive elements and route clicks in `main.js`.

### 6.3 `innerHTML` Template Strings in Render Modules

**Risk: XSS**
- The current code uses `escapeHtml()` inconsistently. When splitting into render modules, each module must call `escapeHtml()` on all user-provided values.
- **Mitigation**: Make `escapeHtml` mandatory. Import it from `utils/escape.js` in every render module. Consider using `textContent` / `document.createElement` for critical fields in a future refactor.

### 6.4 Build Step Decision

**Option A: No build step (recommended for Phase 1)**
- Use ES modules (`type="module"`) with `<link>` for CSS and `<script>` for JS
- Server.cjs serves all files as-is
- Pros: Zero dependencies, instant iteration, matches current "no build" philosophy
- Cons: Multiple HTTP requests, no minification, no tree-shaking

**Option B: Simple build step (recommended for Phase 2)**
- Use a lightweight bundler like esbuild or Vite
- Produces single `dist/paper-lib.css` and `dist/paper-lib.js`
- Pros: Single file, minified, fast load, source maps for development
- Cons: Adds build dependency, CI/deploy complexity

**Recommendation**: Start with Option A (ES modules, no build). The app is small enough (~35KB total) that splitting into ~20 files has negligible performance impact on a local network. If performance becomes an issue (e.g., remote access), add esbuild later. The file structure proposed in Section 2 supports both approaches -- the `dist/` directory is where built output would go.

### 6.5 Data File Location

**Risk**: `index.jsonl` lives at `/opt/fastgpt/4.9.8/static-assets/index.jsonl` (parent directory), not inside `paper-lib/`. The current `INDEX_FILE` path is `/static-assets/index.jsonl` which works from both FastGPT and nginx serving contexts.
- **Mitigation**: Keep the path as `/static-assets/index.jsonl` (absolute from web root). Do not move the data file.

### 6.6 API Base Detection

The current `API_BASE` logic depends on `location.port === '3000'` to detect FastGPT vs nginx context. This is fragile (breaks if FastGPT runs on a different port).
- **Mitigation**: Keep this pattern for backward compatibility but add a `data-api-base` attribute on the `<html>` tag that can be set by the serving environment. Fall back to port detection.

### 6.7 `server.cjs` Static File Serving

Currently `server.cjs` serves files from `ROOT` (the `paper-lib/` directory). If we add a `src/` subdirectory, the existing routes will still work since `server.cjs` uses `path.join(ROOT, req.url)` for static files.
- **Impact**: None. The `src/` files will be served as static files by `server.cjs` at `/src/css/base.css`, `/src/js/main.js`, etc.
- **Note**: The `index.html` should stay at the root of `paper-lib/` so the URL `/paper-lib/index.html` remains unchanged. Put source files in `src/` subdirectory.

## 7. Implementation Sequence

### Phase 1: CSS Extraction (lowest risk, immediate benefit)

1. Create `src/css/` directory with all CSS files per Section 4
2. Extract CSS rules from the `<style>` block into their respective files
3. Add CSS custom properties to `base.css`
4. Replace `<style>` block in `index.html` with `<link>` tags
5. Test thoroughly: verify all visual elements render identically

### Phase 2: JavaScript Modularization

1. Create `src/js/` directory structure
2. Extract `state.js` first (all globals into a shared state object)
3. Extract `utils/escape.js`
4. Extract `api.js` (API_BASE, trackView, fetchRankings)
5. Extract `data.js` (loadPapersData)
6. Extract `search.js` (searchPapersLocal, extractTopics)
7. Extract render modules one at a time, testing each:
   - `render/stats.js`
   - `render/filters.js`
   - `render/papers.js`
   - `render/pagination.js`
   - `render/trending.js`
   - `render/modal.js`
8. Extract action modules:
   - `actions/export.js`
   - `actions/pdf.js`
   - `actions/tracking.js`
9. Wire up `main.js` as the entry point with all imports
10. Replace inline handlers with `addEventListener` in `main.js`
11. Replace `<script>` block with `<script type="module" src="./src/js/main.js">`
12. Test all interactions: search, filter, sort, paginate, modal, export, trending

### Phase 3: Cleanup and Optimization

1. Add `.gitignore` entries for `dist/` and build artifacts
2. Update `CLAUDE.md` with new file structure
3. Update `server.cjs` MIME types if needed (already includes `.js` and `.css`)
4. Consider adding a simple build script (`build.sh` using esbuild) for production output
5. Add `data-api-base` attribute for environment-agnostic API base detection

### Phase 4 (Optional): Build Pipeline

1. Add `package.json` with esbuild as devDependency
2. Create `build.mjs` script that bundles all JS and CSS
3. Output to `dist/` directory
4. Update nginx/FastGPT to serve from `dist/` in production
5. Keep `src/` for development, `dist/` for production

## 8. Key Implementation Details

### 8.1 Event Delegation Pattern

Replace all inline `onclick` with event delegation in `main.js`:

```js
document.addEventListener('DOMContentLoaded', () => {
  // Search button
  document.getElementById('searchBtn')?.addEventListener('click', searchPapers);

  // Paper list (delegated)
  document.getElementById('papersList')?.addEventListener('click', (e) => {
    const card = e.target.closest('.paper-card');
    if (!card) return;
    const paperId = card.dataset.id;

    if (e.target.closest('.paper-title') || e.target.closest('[data-action="preview"]')) {
      showPaper(paperId);
    } else if (e.target.closest('input[type="checkbox"]')) {
      toggleSelect(paperId);
    } else if (e.target.closest('[data-action="download"]')) {
      downloadPaper(paperId);
    } else if (e.target.closest('[data-action="cite"]')) {
      exportCitation(paperId);
    }
  });

  // Year pills container (delegated)
  document.getElementById('yearFilters')?.addEventListener('click', (e) => {
    const pill = e.target.closest('.year-pill[data-year]');
    if (pill) toggleYear(pill.dataset.year);
  });

  // Trending tabs
  document.querySelector('.trending-tabs')?.addEventListener('click', (e) => {
    const tab = e.target.closest('.trending-tab[data-window]');
    if (tab) loadTrending(tab.dataset.window);
  });

  // Trending list (delegated)
  document.getElementById('trendingList')?.addEventListener('click', (e) => {
    const item = e.target.closest('.trending-item[data-id]');
    if (item) showPaper(item.dataset.id);
  });

  // Modal close
  document.getElementById('modalCloseBtn')?.addEventListener('click', closeModal);
  document.getElementById('paperModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'paperModal') closeModal();
  });

  // Sort
  document.getElementById('sortSelect')?.addEventListener('change', sortPapers);

  // Bulk actions
  document.getElementById('exportBtn')?.addEventListener('click', exportSelected);
  document.getElementById('clearBtn')?.addEventListener('click', clearSelection);

  // Modal actions
  document.getElementById('togglePreviewBtn')?.addEventListener('click', togglePreview);
  document.getElementById('downloadBtn')?.addEventListener('click', () => downloadPaper());
  document.getElementById('exportCitationBtn')?.addEventListener('click', () => exportCitation());
});
```

### 8.2 Paper Card Template (in render/papers.js)

```js
import { escapeHtml } from '../utils/escape.js';

export function renderPaperCard(paper, isSelected) {
  return `
    <div class="paper-card" data-id="${escapeHtml(paper.paper_id)}">
      <div style="display: flex; gap: 0.75rem; align-items: flex-start;">
        <input type="checkbox" ${isSelected ? 'checked' : ''} style="margin-top: 0.25rem;">
        <div style="flex: 1;">
          <h3 class="paper-title" data-action="preview">${escapeHtml(paper.title || 'Untitled')}</h3>
          <p class="paper-authors">${escapeHtml((paper.authors || []).join(', ') || 'Unknown authors')}</p>
          <div class="paper-meta">
            ${paper.year ? `<span>${paper.year}</span>` : ''}
            ${paper.venue ? `<span>${escapeHtml(paper.venue)}</span>` : ''}
            ${paper.doi ? `<span class="tag doi">DOI: ${escapeHtml(paper.doi)}</span>` : ''}
          </div>
          <div class="paper-tags">
            ${(paper.tags || []).slice(0, 5).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
          </div>
          <div class="paper-actions">
            <button class="action-btn" data-action="preview">Preview</button>
            <button class="action-btn" data-action="download">Download</button>
            <button class="action-btn" data-action="cite">Cite</button>
          </div>
        </div>
      </div>
    </div>
  `;
}
```

### 8.3 Circular Dependency Avoidance

The `main.js` imports `render/papers.js`, and `render/papers.js` previously called `showPaper` from `render/modal.js` and `toggleSelect` from `main.js`. To avoid circular dependencies:

- Put event-triggering functions (`searchPapers`, `applyFilters`, `sortPapers`) in `main.js`
- Put rendering functions in `render/*.js` that are **pure** (receive data, return HTML strings)
- Use event delegation for all user interactions -- render modules only generate HTML with `data-action` attributes, and `main.js` handles the click routing
- This keeps the dependency graph **acyclic**: `main.js` -> `render/*` but never the reverse

## 9. Testing Strategy

Since there is no test framework currently:

1. **Manual checklist** after each phase:
   - Search works (empty query, partial match, no results)
   - Year filter toggles (single, multiple, clear)
   - Source filter checkboxes
   - Topic tag clicks
   - Sort by year/title/relevance
   - Pagination (first, last, middle, edge pages)
   - Paper modal opens with correct data
   - PDF preview toggle
   - BibTeX export (single, bulk)
   - Trending loads and tabs switch
   - Responsive layout at mobile width

2. **Network tab verification**: Confirm API calls go to correct endpoints in both FastGPT and nginx contexts

3. **Console errors**: Verify zero console errors on load and during interactions

## 10. Summary Recommendation

**Keep it as a no-build-step project using ES modules.** The application is small (~35KB total), serves a local/internal audience, and the "no build step" constraint is a feature not a limitation for this use case. The proposed file structure supports adding a bundler later if needed.

The primary benefits of splitting are:
- Maintainability: each concern in its own file
- Collaboration: multiple developers can work on different modules without merge conflicts
- Testability: isolated functions are easier to unit test
- Readability: finding "where does X happen" is instant instead of searching a 694-line file

The main cost is the multi-file HTTP requests, which are negligible on a local network and can be eliminated with a build step later without restructuring the source.

### Critical Files for Implementation
- /opt/fastgpt/4.9.8/static-assets/index.html (source monolith to be split)
- /opt/fastgpt/4.9.8/static-assets/paper-lib/server.cjs (backend, must serve new file structure)
- /etc/nginx/conf.d/huagpt.huamedicine.com.conf (nginx proxy config, may need path updates)
- /opt/fastgpt/4.9.8/static-assets/paper-lib/CLAUDE.md (update with new structure)
- /opt/fastgpt/4.9.8/static-assets/index.jsonl (data file, location unchanged)
