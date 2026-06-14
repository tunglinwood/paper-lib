# Embeddable Paper Preview — Developer Guide

## Overview

The Paper Library provides an embeddable preview widget that other services can integrate to display paper metadata and PDF previews without building their own UI. It works via iframe embedding or direct navigation.

**Base URL**: `https://174.1.21.3/static-assets`

---

## 1. API Endpoint

### `GET /api/paper`

Fetch paper metadata as JSON. Use this to check if a paper exists before embedding, or to retrieve data for custom UIs.

**Request**
```
GET https://174.1.21.3/static-assets/api/paper?paper_id=sha256_ea73d268fd4a75488b9e8fdc15e5fae09b3c67d7a5793f5c097f8a4237971cce
```

**Response 200**
```json
{
  "paper_id": "sha256_ea73d268fd4a75488b9e8fdc15e5fae09b3c67d7a5793f5c097f8a4237971cce",
  "title": "Application and Development of Continuous Glucose Monitoring in Diabetes Management",
  "authors": ["FENG Lingge"],
  "year": 2023,
  "venue": "Progress in Pharmaceutical Sciences",
  "doi": "10.20053/j.issn1001-5094.2023.10.009",
  "notes": "The use of continuous glucose monitoring...",
  "tags": ["CGM", "Diabetes"],
  "file_path": "01_curated/original/sha256_ea73d268fd4a75488b9e8fdc15e5fae09b3c67d7a5793f5c097f8a4237971cce.pdf",
  "file_size_bytes": 1234567
}
```

**Response 400** — Missing `paper_id` parameter
```json
{ "error": "paper_id parameter required" }
```

**Response 404** — Paper not found
```json
{ "error": "Paper not found" }
```

**CORS**: All responses include `Access-Control-Allow-Origin: *`, so you can call this from any domain.

---

## 2. Embed Page

### `GET /embed.html`

A self-contained HTML page that renders paper metadata and an optional PDF preview iframe. No external dependencies — all CSS and JS are inline.

**URL Parameters**

| Param | Required | Default | Description |
|-------|----------|---------|-------------|
| `paper_id` | Yes | — | The paper's SHA256 ID |
| `mode` | No | `full` | Layout mode: `full` or `sidebar` |
| `show_pdf` | No | `0` | Set to `1` to auto-load PDF preview |

### Mode: `full`

Wide, centered layout suitable for standalone pages or large iframes.

```
https://174.1.21.3/static-assets/embed.html?paper_id=sha256_ea73d268...
```

### Mode: `sidebar`

Narrow layout (max 400px) with a close button in the top-right corner. Designed for right-side panels or narrow iframes.

```
https://174.1.21.3/static-assets/embed.html?paper_id=sha256_ea73d268...&mode=sidebar
```

### Auto-show PDF

Add `&show_pdf=1` to immediately load the PDF iframe when the page opens.

```
https://174.1.21.3/static-assets/embed.html?paper_id=sha256_ea73d268...&mode=sidebar&show_pdf=1
```

---

## 3. Integration Examples

### iframe Embedding (Recommended)

The simplest integration. Embed the preview in a sidebar, modal, or panel.

```html
<div id="paper-preview-container">
  <iframe
    id="paper-preview"
    src="https://174.1.21.3/static-assets/embed.html?paper_id=SHA256_HERE&mode=sidebar"
    width="400"
    height="800"
    style="border: none; border-radius: 8px;"
    allowfullscreen
  ></iframe>
</div>
```

### React Component

```tsx
interface PaperPreviewProps {
  paperId: string;
  mode?: 'full' | 'sidebar';
  showPdf?: boolean;
}

const EMBED_BASE = 'https://174.1.21.3/static-assets';

function PaperPreview({ paperId, mode = 'full', showPdf = false }: PaperPreviewProps) {
  const params = new URLSearchParams({ paper_id: paperId });
  if (mode === 'sidebar') params.set('mode', 'sidebar');
  if (showPdf) params.set('show_pdf', '1');

  return (
    <iframe
      src={`${EMBED_BASE}/embed.html?${params.toString()}`}
      width={mode === 'sidebar' ? 400 : '100%'}
      height={mode === 'sidebar' ? 800 : 600}
      style={{ border: 'none' }}
      allowFullScreen
    />
  );
}
```

### Vue Component

```vue
<template>
  <iframe
    :src="embedUrl"
    :width="mode === 'sidebar' ? 400 : '100%'"
    :height="mode === 'sidebar' ? 800 : 600"
    style="border: none;"
    allowfullscreen
  />
</template>

<script setup>
const props = defineProps({
  paperId: { type: String, required: true },
  mode: { type: String, default: 'full' },
  showPdf: { type: Boolean, default: false },
});

const EMBED_BASE = 'https://174.1.21.3/static-assets';

const embedUrl = computed(() => {
  const params = new URLSearchParams({ paper_id: props.paperId });
  if (props.mode === 'sidebar') params.set('mode', 'sidebar');
  if (props.showPdf) params.set('show_pdf', '1');
  return `${EMBED_BASE}/embed.html?${params.toString()}`;
});
</script>
```

### Dynamic paper switching

When the user selects different papers, update the iframe's `src`:

```javascript
function showPaper(paperId) {
  const iframe = document.getElementById('paper-preview');
  iframe.src = `https://174.1.21.3/static-assets/embed.html?paper_id=${paperId}&mode=sidebar`;
}
```

---

## 4. Cross-Origin Communication (postMessage)

The embed page sends messages to the parent window for certain events.

### Close Event

When the user clicks the "Close" button (visible in `sidebar` mode), the embed page sends:

```javascript
{ type: 'paper-preview-close' }
```

Listen for this in your host page:

```javascript
window.addEventListener('message', (event) => {
  if (event.data?.type === 'paper-preview-close') {
    // Hide your sidebar/modal
    document.getElementById('paper-preview-container').style.display = 'none';
  }
});
```

---

## 5. PDF URL Construction

If you need to build a direct PDF link (e.g., for a download button in your own UI):

```
https://174.1.21.3/static-assets/archive/_unsorted/Library/{file_path}
```

Where `{file_path}` comes from the `/api/paper` response. Example:

```
https://174.1.21.3/static-assets/archive/_unsorted/Library/01_curated/original/sha256_ea73d268...pdf
```

---

## 6. Error Handling

The embed page handles errors internally and displays user-friendly messages:

- **Missing `paper_id`**: Shows "Missing paper_id" with instructions
- **Paper not found** (404): Shows "Paper not found"
- **Server error**: Shows "Server error"

You can also pre-validate with the API before embedding:

```javascript
async function canEmbed(paperId) {
  const resp = await fetch(`https://174.1.21.3/static-assets/api/paper?paper_id=${paperId}`);
  return resp.ok;
}
```

---

## 7. Access via Nginx

The embed page and API are accessible through the nginx reverse proxy at `https://174.1.21.3/static-assets/`. This provides:
- SSL/TLS termination
- Mixed-content-safe access from HTTPS pages
- CORS headers on API responses

If accessing from `huagpt.meta-stone.net`, the same URLs work via the external proxy routing.

---

## Quick Reference

| What | URL |
|------|-----|
| Paper metadata | `GET /static-assets/api/paper?paper_id={id}` |
| Preview (full) | `/static-assets/embed.html?paper_id={id}` |
| Preview (sidebar) | `/static-assets/embed.html?paper_id={id}&mode=sidebar` |
| Preview + PDF | `/static-assets/embed.html?paper_id={id}&mode=sidebar&show_pdf=1` |
| Direct PDF | `/static-assets/archive/_unsorted/Library/{file_path}` |
