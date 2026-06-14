// API configuration and fetch wrappers
// After deployment restructure: frontend and backend share same origin.
// API_BASE is empty string — all API calls use relative paths (/api/*).
// When served via Bun dev server: API requests are proxied to backend (:8000).
// When served directly by backend (FastAPI): API routes are on same origin.
export const API_BASE = '';
export const PDF_BASE = '/archive/_unsorted/Library/';

export async function fetchIndex() {
    const response = await fetch(`${API_BASE}/api/papers?_t=${Date.now()}`);
    return response.json();
}

export async function trackView(paperId, type = 'preview') {
    try {
        await fetch(`${API_BASE}/api/track-view`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId, type }),
        });
    } catch { /* silently fail */ }
}

export async function fetchRankings(windowDays = '7') {
    const resp = await fetch(`${API_BASE}/api/rankings?window=${windowDays}`);
    return resp.json();
}

export async function deletePapers(paperIds) {
    const resp = await fetch(`${API_BASE}/api/admin/delete-papers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: paperIds }),
    });
    return resp.json();
}

export async function updatePaper(paperId, updates) {
    const resp = await fetch(`${API_BASE}/api/admin/update-paper`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paperId, updates }),
    });
    return resp.json();
}

export async function crawlPdfMetadata(paperId) {
    const resp = await fetch(`${API_BASE}/api/admin/crawl-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paperId }),
    });
    return resp.json();
}

export async function generateHtml(paperId) {
    const resp = await fetch(`${API_BASE}/api/admin/generate-html`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paperId }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Generate HTML failed');
    return data;
}

export async function searchPapers(params = {}) {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.year_from) qs.set('year_from', params.year_from);
    if (params.year_to) qs.set('year_to', params.year_to);
    if (params.source) qs.set('source', params.source);
    if (params.venue) qs.set('venue', params.venue);
    if (params.sort) qs.set('sort', params.sort);
    if (params.page) qs.set('page', params.page);
    if (params.page_size) qs.set('page_size', params.page_size);
    if (params.include) qs.set('include', params.include);

    const resp = await fetch(`${API_BASE}/api/search?${qs}`);
    return resp.json();
}

export async function uploadAndCrawl(file) {
    const form = new FormData();
    form.append('file', file);
    const resp = await fetch(`${API_BASE}/api/admin/upload-and-crawl`, {
        method: 'POST',
        body: form,
    });
    return resp.json();
}

export async function confirmPapers(papers) {
    const resp = await fetch(`${API_BASE}/api/admin/confirm-papers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ papers }),
    });
    return resp.json();
}
