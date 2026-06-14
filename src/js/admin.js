import { state } from './state.js';
import { fetchIndex, searchPapers, deletePapers, updatePaper, crawlPdfMetadata, generateHtml, uploadAndCrawl, confirmPapers, PDF_BASE } from './api.js';
import { escapeHtml, formatSize } from './utils/helpers.js';
import { setupPanelResize } from './render/modal.js';

// --- Data loading ---
async function loadPapersData() {
    const papers = await fetchIndex();
    state.allPapers = papers;
    state.filteredPapers = [...papers];
    return papers;
}

function refreshCounts() {
    const total = state.allPapers.length;
    const shown = state.filteredPapers.length;
    document.getElementById('papersCount').textContent =
        `${shown} of ${total} papers`;
}

function refreshStats() {
    const papers = state.allPapers;
    const totalEl = document.getElementById('statTotalPapers');
    if (totalEl) totalEl.textContent = papers.length;

    const totalBytes = papers.reduce((sum, p) => sum + (p.file_size_bytes || 0), 0);
    const sizeEl = document.getElementById('statTotalSize');
    if (sizeEl) sizeEl.textContent = formatSize(totalBytes);

    const venues = new Set(papers.map(p => p.venue).filter(Boolean));
    const venuesEl = document.getElementById('statVenues');
    if (venuesEl) venuesEl.textContent = venues.size;

    const years = papers.map(p => p.year).filter(Boolean);
    const yearsEl = document.getElementById('statYears');
    if (yearsEl) {
        yearsEl.textContent = years.length > 0 ? `${Math.min(...years)}–${Math.max(...years)}` : '-';
    }
}

// --- Table rendering ---
async function searchAndRender() {
    const queryStr = document.getElementById('searchInput').value;
    const q = queryStr.trim();

    if (!q) {
        state.filteredPapers = [...state.allPapers];
        applySort();
        renderTableBody();
        return;
    }

    try {
        const resp = await searchPapers({ q });
        state.filteredPapers = resp.results;
        // Results come back relevance-sorted from API; don't re-sort
        renderTableBody();
    } catch (err) {
        console.error('Search failed:', err);
        state.filteredPapers = [...state.allPapers];
        applySort();
        renderTableBody();
    }
}

function applySort() {
    const sort = document.getElementById('sortSelect').value;
    if (sort === 'year') {
        state.filteredPapers.sort((a, b) => (b.year || 0) - (a.year || 0));
    } else if (sort === 'title') {
        state.filteredPapers.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (sort === 'source') {
        state.filteredPapers.sort((a, b) => (a.source || '').localeCompare(b.source || ''));
    } else {
        state.filteredPapers.sort((a, b) => (b.year || 0) - (a.year || 0));
    }
}

function renderTableBody() {
    const tbody = document.getElementById('paperTableBody');
    const results = state.filteredPapers;
    refreshCounts();

    if (results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No papers found.</td></tr>';
        return;
    }

    tbody.innerHTML = results.map(paper => `
        <tr data-id="${paper.paper_id}">
            <td class="col-checkbox">
                <input type="checkbox" data-action="toggle-select" data-id="${paper.paper_id}">
            </td>
            <td class="col-title">
                <span class="paper-title-link" data-action="preview-paper" data-id="${paper.paper_id}" title="${escapeHtml(paper.title || '')}">
                    ${escapeHtml(paper.title || 'Untitled')}
                </span>
            </td>
            <td class="col-authors" title="${escapeHtml((paper.authors || []).join(', ') || 'Unknown')}">
                ${escapeHtml((paper.authors || ['Unknown']).slice(0, 2).join(', '))}${(paper.authors || []).length > 2 ? '...' : ''}
            </td>
            <td class="col-year">${paper.year || '—'}</td>
            <td class="col-source" title="${escapeHtml(paper.source || '')}">
                ${escapeHtml(paper.source || '—')}
            </td>
            <td class="col-venue" title="${escapeHtml(paper.venue || '')}">
                ${escapeHtml(paper.venue || '—')}
            </td>
            <td class="col-size">${formatSize(paper.file_size_bytes)}</td>
            <td class="col-actions">
                <div class="table-actions">
                    <button class="table-btn" data-action="crawl-pdf" data-id="${paper.paper_id}">crawl4ai</button>
                    ${!paper.html_path && paper.file_path
                        ? `<button class="table-btn html" data-action="generate-html" data-id="${paper.paper_id}">Gen HTML</button>`
                        : paper.html_path
                            ? `<button class="table-btn html" data-action="view-html" data-id="${paper.paper_id}">View HTML</button>`
                            : ''}
                    <button class="table-btn danger" data-action="delete-paper" data-id="${paper.paper_id}">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');
}



// --- Selection ---
function toggleSelect(paperId) {
    if (state.selectedPapers.has(paperId)) state.selectedPapers.delete(paperId);
    else state.selectedPapers.add(paperId);
    updateBulkActions();
    updateSelectAllCheckbox();
}

function toggleSelectAll() {
    const checked = document.getElementById('selectAll').checked;
    state.filteredPapers.forEach(p => {
        if (checked) state.selectedPapers.add(p.paper_id);
        else state.selectedPapers.delete(p.paper_id);
    });
    // Update all checkboxes in table
    document.querySelectorAll('#paperTableBody input[type="checkbox"]').forEach(cb => {
        cb.checked = checked;
    });
    updateBulkActions();
}

function updateSelectAllCheckbox() {
    const selectAll = document.getElementById('selectAll');
    if (state.filteredPapers.length === 0) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
    } else {
        const filteredIds = new Set(state.filteredPapers.map(p => p.paper_id));
        const selectedInFilter = [...state.selectedPapers].filter(id => filteredIds.has(id)).length;
        selectAll.checked = selectedInFilter === state.filteredPapers.length && state.filteredPapers.length > 0;
        selectAll.indeterminate = selectedInFilter > 0 && selectedInFilter < state.filteredPapers.length;
    }
}

function updateBulkActions() {
    const bulk = document.getElementById('bulkActions');
    const count = state.selectedPapers.size;
    bulk.classList.toggle('active', count > 0);
    document.getElementById('selectedCount').textContent = `${count} selected`;
}

function clearSelection() {
    state.selectedPapers.clear();
    document.getElementById('selectAll').checked = false;
    document.getElementById('selectAll').indeterminate = false;
    document.querySelectorAll('#paperTableBody input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    updateBulkActions();
}

// --- Preview / Edit in place ---
function showPaper(paperId) {
    const paper = state.allPapers.find(p => p.paper_id === paperId);
    if (!paper) return;
    state.currentPaper = paper;

    document.getElementById('modalTitle').textContent = paper.title || 'Untitled';
    document.getElementById('modalAuthors').textContent = (paper.authors || []).join(', ') || 'Unknown authors';

    // Populate editable fields
    document.getElementById('metaTitle').value = paper.title || '';
    document.getElementById('metaYear').value = paper.year || '';
    document.getElementById('metaSource').value = paper.source || '';
    document.getElementById('metaAuthors').value = (paper.authors || []).join(', ');
    document.getElementById('metaVenue').value = paper.venue || '';
    document.getElementById('metaDoi').value = paper.doi || '';
    document.getElementById('metaTags').value = (paper.tags || []).join(', ');
    document.getElementById('metaAbstract').value = paper.abstract || '';

    // Set PDF viewer
    if (paper.file_path) {
        document.getElementById('pdfViewerContainer').style.display = 'block';
        document.getElementById('pdfPreview').src = PDF_BASE + paper.file_path;
    } else {
        document.getElementById('pdfViewerContainer').style.display = 'none';
        document.getElementById('pdfPreview').src = '';
    }

    // Toggle View HTML / Generate HTML buttons
    const viewHtmlBtn = document.getElementById('viewHtmlBtn');
    const generateHtmlBtn = document.getElementById('generateHtmlBtn');
    if (viewHtmlBtn) viewHtmlBtn.style.display = paper.html_path ? '' : 'none';
    if (generateHtmlBtn) generateHtmlBtn.style.display = (!paper.html_path && paper.file_path) ? '' : 'none';

    document.getElementById('paperModal').classList.add('active');
}

function closeModal() {
    document.getElementById('paperModal').classList.remove('active');
    document.getElementById('pdfViewerContainer').style.display = 'none';
    document.getElementById('pdfPreview').src = '';
    state.currentPaper = null;
}

async function saveMetaChanges() {
    if (!state.currentPaper) return;

    const btn = document.getElementById('saveMetaBtn');
    btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17,21 17,13 7,13 7,21"/><polyline points="7,3 7,8 15,8"/></svg>Saving...`;
    btn.disabled = true;

    const updates = {
        title: document.getElementById('metaTitle').value.trim(),
        year: parseInt(document.getElementById('metaYear').value) || null,
        source: document.getElementById('metaSource').value.trim(),
        authors: document.getElementById('metaAuthors').value.split(',').map(s => s.trim()).filter(Boolean),
        venue: document.getElementById('metaVenue').value.trim(),
        doi: document.getElementById('metaDoi').value.trim(),
        tags: document.getElementById('metaTags').value.split(',').map(s => s.trim()).filter(Boolean),
        abstract: document.getElementById('metaAbstract').value.trim(),
    };

    try {
        const result = await updatePaper(state.currentPaper.paper_id, updates);
        if (result.ok) {
            await loadPapersData();
            searchAndRender();
            // Refresh current paper in state
            const updated = state.allPapers.find(p => p.paper_id === state.currentPaper.paper_id);
            if (updated) {
                state.currentPaper = updated;
            }
        } else {
            alert(`Update failed: ${result.error || 'Unknown error'}`);
        }
    } catch (err) {
        alert(`Update failed: ${err.message}`);
    } finally {
        btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17,21 17,13 7,13 7,21"/><polyline points="7,3 7,8 15,8"/></svg>Save`;
        btn.disabled = false;
    }
}

// --- Upload (3-stage pipeline) ---
let selectedFiles = [];
let pendingReviewData = [];
let currentUploadStage = 1;

function goToStage(stage) {
    currentUploadStage = stage;
    const titleEl = document.getElementById('uploadModalTitle');
    for (let i = 1; i <= 3; i++) {
        const el = document.getElementById(`uploadStage${i}`);
        if (el) el.style.display = i === stage ? '' : 'none';
    }
    const titles = { 1: 'Upload Papers', 2: 'Uploading & Extracting...', 3: 'Review & Confirm' };
    if (titleEl) titleEl.textContent = titles[stage] || 'Upload Papers';
}

function openUploadModal() {
    goToStage(1);
    selectedFiles = [];
    pendingReviewData = [];
    document.getElementById('uploadFile').value = '';
    document.getElementById('uploadFileList').style.display = 'none';
    document.getElementById('uploadStartBtn').disabled = true;
    document.getElementById('uploadModal').classList.add('active');
}

function closeUploadModal() {
    document.getElementById('uploadModal').classList.remove('active');
    goToStage(1);
    selectedFiles = [];
    pendingReviewData = [];
    document.getElementById('uploadFile').value = '';
    document.getElementById('uploadFileList').style.display = 'none';
    document.getElementById('uploadStartBtn').disabled = true;
}

function triggerFileSelect() {
    document.getElementById('uploadFile').click();
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) {
        selectedFiles = [];
        document.getElementById('uploadFileList').style.display = 'none';
        document.getElementById('uploadStartBtn').disabled = true;
        return;
    }

    selectedFiles = files;
    document.getElementById('uploadFileList').style.display = '';
    document.getElementById('uploadStartBtn').disabled = false;
    renderFileList();
}

function renderFileList() {
    const tbody = document.getElementById('uploadFileListBody');
    if (selectedFiles.length === 0) return;

    tbody.innerHTML = selectedFiles.map((file, idx) => `
        <tr data-file-idx="${idx}">
            <td class="col-remove">
                <button type="button" class="remove-file-btn" data-action="remove-file" data-file-idx="${idx}" title="Remove">&times;</button>
            </td>
            <td class="col-filename" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</td>
            <td class="col-size">${formatSize(file.size)}</td>
        </tr>
    `).join('');
}

function removeFile(idx) {
    selectedFiles.splice(idx, 1);
    if (selectedFiles.length === 0) {
        document.getElementById('uploadFileList').style.display = 'none';
        document.getElementById('uploadStartBtn').disabled = true;
        document.getElementById('uploadFile').value = '';
        return;
    }
    renderFileList();
}

// Stage 2: Progress
function renderProgressList() {
    const list = document.getElementById('uploadProgressList');
    list.innerHTML = selectedFiles.map((file, idx) => `
        <div class="upload-progress-item" id="uploadProgress-${idx}">
            <span class="upload-progress-status" id="uploadStatus-${idx}">&#9201;</span>
            <span class="upload-progress-label" id="uploadLabel-${idx}">${escapeHtml(file.name)}</span>
            <div class="upload-progress-bar-container">
                <div class="upload-progress-bar" id="uploadBar-${idx}" style="width:0%"></div>
            </div>
        </div>
    `).join('');
    document.getElementById('uploadSummary').style.display = 'none';
}

function updateProgressItem(idx, status, label) {
    const bar = document.getElementById(`uploadBar-${idx}`);
    const statusEl = document.getElementById(`uploadStatus-${idx}`);
    const labelEl = document.getElementById(`uploadLabel-${idx}`);
    if (bar && status === 'done') bar.style.width = '100%';
    if (bar && status === 'error') { bar.style.width = '100%'; bar.classList.add('error'); }
    if (statusEl) {
        const icons = { uploading: '&#8987;', extracting: '&#128269;', done: '&#9989;', error: '&#10060;', duplicate: '&#9888;' };
        statusEl.innerHTML = icons[status] || '';
    }
    if (labelEl) labelEl.textContent = label || '';
}

// Stage 3: Review
function renderReviewCards(reviewData) {
    const list = document.getElementById('reviewList');
    list.innerHTML = reviewData.map((paper, idx) => {
        const isDup = paper.extract_status === 'duplicate';
        const isError = paper.extract_status === 'error';
        const isIncomplete = !paper.title || paper.title === 'Untitled' || !paper.year || (paper.authors && paper.authors.length === 0);
        const cardClass = isDup ? 'duplicate' : isError ? 'error' : isIncomplete ? 'incomplete' : 'extracted';
        const statusText = isDup ? 'Already exists' : isError ? 'Extraction failed' : isIncomplete ? 'Incomplete' : 'Extracted';
        const statusClass = isDup ? 'duplicate' : isError ? 'error' : isIncomplete ? 'incomplete' : 'extracted';

        const authorsStr = (paper.authors || []).join(', ') || '';
        const yearStr = paper.year || '';
        const venueStr = paper.venue || '';
        const doiStr = paper.doi || '';
        const abstractStr = paper.abstract || '';

        return `
            <div class="review-card ${cardClass}" data-review-idx="${idx}">
                <div class="review-card-header">
                    <span class="review-card-filename">${escapeHtml(paper.filename || 'Unknown')}</span>
                    <span class="review-card-status ${statusClass}">${statusText}</span>
                </div>
                <div class="review-card-body">
                    <span class="review-field-label">Title</span>
                    ${isDup ? `<span class="review-field-value">${escapeHtml(paper.title || 'N/A')}</span>` :
                        `<input class="review-field-input" data-review-field="title" data-review-idx="${idx}" value="${escapeHtml(paper.title || '')}" placeholder="Enter title">`}
                    ${isDup ? '' : `
                    <span class="review-field-label">Authors</span>
                    <input class="review-field-input" data-review-field="authors" data-review-idx="${idx}" value="${escapeHtml(authorsStr)}" placeholder="Author1, Author2">
                    <span class="review-field-label">Year</span>
                    <input class="review-field-input" data-review-field="year" data-review-idx="${idx}" value="${escapeHtml(yearStr)}" placeholder="2024" style="width:100px;">
                    ${venueStr || isIncomplete ? `
                    <span class="review-field-label">Venue</span>
                    <input class="review-field-input" data-review-field="venue" data-review-idx="${idx}" value="${escapeHtml(venueStr)}" placeholder="Journal name">` : ''}
                    ${doiStr || isIncomplete ? `
                    <span class="review-field-label">DOI</span>
                    <input class="review-field-input" data-review-field="doi" data-review-idx="${idx}" value="${escapeHtml(doiStr)}" placeholder="10.xxxx/..." style="width:200px;">` : ''}
                    ${abstractStr ? `
                    <span class="review-field-label">Abstract</span>
                    <textarea class="review-field-input" data-review-field="abstract" data-review-idx="${idx}" rows="2" placeholder="Abstract">${escapeHtml(abstractStr)}</textarea>` : ''}
                    `}
                </div>
            </div>
        `;
    }).join('');
}

// Core pipeline
async function startUploadPipeline() {
    if (selectedFiles.length === 0) return;

    goToStage(2);
    renderProgressList();

    // Concurrent uploads
    const uploadPromises = selectedFiles.map((file, idx) =>
        uploadAndCrawl(file)
            .then(result => ({ idx, file, result, status: 'done' }))
            .catch(err => ({ idx, file, result: null, status: 'error', error: err.message }))
    );

    const results = await Promise.all(uploadPromises);

    // Build review data
    const reviewData = results.map(r => {
        if (r.result?.status === 'duplicate') {
            return {
                paper_id: r.result.paper_id,
                file_path: '',
                file_size_bytes: 0,
                filename: r.file.name,
                title: r.result.title || r.file.name.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '),
                authors: [],
                year: null,
                venue: '',
                doi: '',
                abstract: '',
                tags: ['Uploaded'],
                source: 'Upload',
                extract_status: 'duplicate',
            };
        }
        const m = r.result?.metadata || {};
        const isError = r.result?.status === 'uploaded_no_extract';
        return {
            paper_id: r.result?.paper_id || '',
            file_path: r.result?.file_path || '',
            html_path: r.result?.html_path || null,
            file_size_bytes: r.result?.file_size_bytes || 0,
            filename: r.file.name,
            title: m?.title || (isError ? r.result?.title : '') || r.file.name.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '),
            authors: m?.authors || [],
            year: m?.year || new Date().getFullYear(),
            venue: m?.venue || '',
            doi: m?.doi || '',
            abstract: m?.abstract || '',
            tags: ['Uploaded'],
            source: 'Upload',
            extract_status: isError ? 'error' : (m?.title ? 'extracted' : 'incomplete'),
        };
    });

    // Update progress UI
    results.forEach(r => {
        const paper = reviewData.find(p => p.filename === r.file.name);
        const status = r.result?.status === 'duplicate' ? 'duplicate' :
                       r.status === 'error' ? 'error' :
                       r.result?.status === 'uploaded_no_extract' ? 'error' : 'done';
        const label = r.result?.status === 'duplicate' ? `${r.file.name} (duplicate of "${r.result.title}")` :
                      r.status === 'error' ? `${r.file.name} (upload failed)` :
                      r.result?.status === 'uploaded_no_extract' ? `${r.file.name} (extraction failed)` :
                      `${r.file.name} — ${paper?.title || 'done'}`;
        updateProgressItem(r.idx, status, label);
    });

    // Pause briefly so user sees the completed progress
    await new Promise(resolve => setTimeout(resolve, 800));

    pendingReviewData = reviewData;
    renderReviewCards(reviewData);

    // Show skip button if any incomplete
    const hasIncomplete = reviewData.some(p => p.extract_status === 'error' || p.extract_status === 'duplicate' || !p.title || p.title === 'Untitled');
    document.getElementById('skipIncompleteBtn').style.display = hasIncomplete ? '' : 'none';

    goToStage(3);
}

async function confirmAllPapers() {
    // Read current values from review inputs
    pendingReviewData.forEach((paper, idx) => {
        const titleInput = document.querySelector(`.review-field-input[data-review-idx="${idx}"][data-review-field="title"]`);
        const authorsInput = document.querySelector(`.review-field-input[data-review-idx="${idx}"][data-review-field="authors"]`);
        const yearInput = document.querySelector(`.review-field-input[data-review-idx="${idx}"][data-review-field="year"]`);
        const venueInput = document.querySelector(`.review-field-input[data-review-idx="${idx}"][data-review-field="venue"]`);
        const doiInput = document.querySelector(`.review-field-input[data-review-idx="${idx}"][data-review-field="doi"]`);
        const abstractInput = document.querySelector(`.review-field-input[data-review-idx="${idx}"][data-review-field="abstract"]`);

        if (titleInput) paper.title = titleInput.value.trim();
        if (authorsInput) paper.authors = authorsInput.value.split(',').map(s => s.trim()).filter(Boolean);
        if (yearInput) paper.year = yearInput.value ? parseInt(yearInput.value, 10) : null;
        if (venueInput) paper.venue = venueInput.value.trim();
        if (doiInput) paper.doi = doiInput.value.trim();
        if (abstractInput) paper.abstract = abstractInput.value.trim();
    });

    // Filter out duplicates and papers without title
    const toConfirm = pendingReviewData.filter(p => p.extract_status !== 'duplicate' && p.title);
    if (toConfirm.length === 0) {
        alert('No papers to confirm.');
        return;
    }

    const btn = document.getElementById('confirmAllBtn');
    btn.textContent = 'Confirming...';
    btn.disabled = true;

    try {
        const result = await confirmPapers(toConfirm);
        if (result.ok) {
            await loadPapersData();
            searchAndRender();
            closeUploadModal();
        } else {
            alert(`Confirmation failed: ${result.error || 'Unknown error'}`);
        }
    } catch (err) {
        alert(`Confirmation failed: ${err.message}`);
    } finally {
        btn.textContent = 'Confirm All';
        btn.disabled = false;
    }
}

function skipIncomplete() {
    // Keep only papers with extracted metadata
    pendingReviewData = pendingReviewData.filter(p => p.extract_status === 'extracted' || p.extract_status === 'incomplete');
    renderReviewCards(pendingReviewData);
    document.getElementById('skipIncompleteBtn').style.display = 'none';
}

// --- Crawl4ai PDF metadata ---
async function crawlPdfMetadataAction(paperId) {
    const paper = state.allPapers.find(p => p.paper_id === paperId);
    if (!paper?.file_path) {
        alert('No PDF file for this paper');
        return;
    }

    if (!confirm(`crawl4ai will extract metadata from the PDF and auto-update the paper.\n\nCurrent: "${paper.title || 'Untitled'}"\n\nContinue?`)) return;

    // Show a simple indicator that it's running
    const btn = document.querySelector(`[data-action="crawl-pdf"][data-id="${paperId}"]`)
        || document.getElementById('crawlPdfBtn');
    if (btn) {
        btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3,6 5,6 21,6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>Extracting...`;
        btn.disabled = true;
    }

    try {
        const result = await crawlPdfMetadata(paperId);
        if (result.ok) {
            const m = result.metadata;
            if (!m) {
                alert('Crawl completed but no metadata was extracted from the PDF.');
                await loadPapersData();
                searchAndRender();
                return;
            }
            const summary = [
                m.title ? `Title: ${m.title}` : null,
                m.authors?.length ? `Authors: ${m.authors.join(', ')}` : null,
                m.year ? `Year: ${m.year}` : null,
                m.venue ? `Venue: ${m.venue}` : null,
                m.doi ? `DOI: ${m.doi}` : null,
            ].filter(Boolean).join('\n');
            alert(`Metadata updated successfully:\n\n${summary || '(no fields extracted)'}`);
            await loadPapersData();
            searchAndRender();
            if (state.currentPaper?.paper_id === paperId) {
                showPaper(paperId);
            }
        } else if (result.error?.includes('Already crawling')) {
            alert('This paper is already being crawled. Please wait for it to finish.');
        } else {
            alert(`crawl4ai failed: ${result.error || 'Unknown error'}`);
        }
    } catch (err) {
        alert(`crawl4ai failed: ${err.message}`);
    } finally {
        if (btn) {
            btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27,6.96 12,12.01 20.73,6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>Crawl PDF`;
            btn.disabled = false;
        }
    }
}

// --- Generate HTML from PDF ---
async function generateHtmlAction(paperId) {
    const paper = state.allPapers.find(p => p.paper_id === paperId);
    if (!paper?.file_path) {
        alert('No PDF file for this paper');
        return;
    }
    if (paper.html_path) {
        alert(`HTML already exists for this paper. Click "View HTML" to open it.`);
        return;
    }

    const title = (paper.title || 'Untitled').slice(0, 80);
    if (!confirm(`Convert this paper's PDF to HTML using pdf2htmlEX?\n\n"${title}"\n\nThis may take 30–60 seconds for large PDFs.`)) return;

    const btn = document.getElementById('generateHtmlBtn');
    if (btn) {
        btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>Converting...`;
        btn.disabled = true;
    }

    try {
        const result = await generateHtml(paperId);
        if (result.ok) {
            // Update local state
            await loadPapersData();
            searchAndRender();
            if (state.currentPaper?.paper_id === paperId) {
                showPaper(paperId);
            }
            alert(`HTML generated successfully!\n\nYou can now view it by clicking "View HTML".`);
        } else {
            alert(`HTML generation failed: ${result.detail || result.error || 'Unknown error'}`);
        }
    } catch (err) {
        const msg = err.message || 'Unknown error';
        if (msg.includes('too large')) {
            alert(`PDF is too large for conversion (max 100MB).`);
        } else if (msg.includes('timed out')) {
            alert(`PDF conversion timed out. The PDF may be too complex or the server is busy.`);
        } else if (msg.includes('Docker') || msg.includes('docker')) {
            alert(`Docker is not available. Please ensure pdf2htmlEX Docker image is installed.`);
        } else {
            alert(`HTML generation failed: ${msg}`);
        }
    } finally {
        if (btn) {
            btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>Generate HTML`;
            btn.disabled = false;
        }
    }
}

// --- Delete ---
let pendingDeleteIds = [];

function showDeleteConfirm(paperIds) {
    pendingDeleteIds = paperIds;
    const msg = paperIds.length === 1
        ? `Are you sure you want to delete this paper? This will remove both the metadata and the PDF file.`
        : `Are you sure you want to delete <strong>${paperIds.length}</strong> papers? This will remove all metadata and PDF files.`;
    document.getElementById('deleteMessage').innerHTML = msg;
    document.getElementById('deleteModal').classList.add('active');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('active');
    pendingDeleteIds = [];
}

async function confirmDelete() {
    if (pendingDeleteIds.length === 0) return;

    const btn = document.getElementById('confirmDeleteBtn');
    btn.textContent = 'Deleting...';
    btn.disabled = true;

    try {
        const result = await deletePapers(pendingDeleteIds);
        if (result.ok) {
            // Reload data
            await loadPapersData();
            searchAndRender();
            clearSelection();
        } else {
            alert(`Delete failed: ${result.error || 'Unknown error'}`);
        }
    } catch (err) {
        alert(`Delete failed: ${err.message}`);
    } finally {
        btn.textContent = 'Delete';
        btn.disabled = false;
        closeDeleteModal();
    }
}

// --- Event delegation ---
function setupEvents() {
    // Table click delegation
    document.getElementById('paperTableBody')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        const action = target.dataset.action;
        const id = target.dataset.id;

        switch (action) {
            case 'toggle-select': toggleSelect(id); break;
            case 'preview-paper': showPaper(id); break;
            case 'delete-paper': showDeleteConfirm([id]); break;
            case 'crawl-pdf': crawlPdfMetadataAction(id); break;
            case 'view-html': window.open(`/papers/${id}.html`, '_blank'); break;
            case 'generate-html': generateHtmlAction(id); break;
        }
    });

    // Select all checkbox
    document.getElementById('selectAll')?.addEventListener('change', toggleSelectAll);

    // Search
    document.querySelector('[data-action="search"]')?.addEventListener('click', searchAndRender);
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchAndRender();
    });

    // Debounced auto-search on input (matches main page behavior)
    let searchDebounce = null;
    document.getElementById('searchInput')?.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => searchAndRender(), 500);
    });

    // Sort
    document.getElementById('sortSelect')?.addEventListener('change', () => {
        applySort();
        renderTableBody();
    });

    // Modal backdrop + actions
    document.getElementById('paperModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'paperModal') {
            closeModal();
            return;
        }
        const target = e.target.closest('[data-action]');
        if (!target) return;
        const action = target.dataset.action;
        const id = target.dataset.id || state.currentPaper?.paper_id;
        switch (action) {
            case 'delete-paper': showDeleteConfirm([id]); break;
            case 'crawl-pdf': crawlPdfMetadataAction(id); break;
            case 'view-html': window.open(`/papers/${id}.html`, '_blank'); break;
            case 'generate-html': generateHtmlAction(id); break;
        }
    });

    document.getElementById('uploadModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'uploadModal') closeUploadModal();
    });

    document.getElementById('deleteModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'deleteModal') closeDeleteModal();
    });

    // Modal buttons
    document.querySelector('.modal-close')?.addEventListener('click', closeModal);
    document.getElementById('saveMetaBtn')?.addEventListener('click', saveMetaChanges);
    document.getElementById('crawlPdfBtn')?.addEventListener('click', (e) => {
        const id = state.currentPaper?.paper_id;
        if (id) crawlPdfMetadataAction(id);
    });
    document.getElementById('generateHtmlBtn')?.addEventListener('click', (e) => {
        const id = state.currentPaper?.paper_id;
        if (id) generateHtmlAction(id);
    });
    document.getElementById('deleteBtn')?.addEventListener('click', (e) => {
        const id = state.currentPaper?.paper_id;
        if (id) showDeleteConfirm([id]);
    });

    // Bulk actions
    document.getElementById('bulkActions')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        switch (target.dataset.action) {
            case 'bulk-delete':
                if (state.selectedPapers.size > 0) showDeleteConfirm([...state.selectedPapers]);
                break;
            case 'clear-selection': clearSelection(); break;
        }
    });

    document.querySelectorAll('[data-action="open-upload"]').forEach(btn => {
        btn.addEventListener('click', openUploadModal);
    });
    document.querySelectorAll('[data-action="close-upload"]').forEach(btn => {
        btn.addEventListener('click', closeUploadModal);
    });
    document.getElementById('uploadFile')?.addEventListener('change', handleFileSelect);
    document.querySelectorAll('[data-action="trigger-file-select"]').forEach(btn => {
        btn.addEventListener('click', triggerFileSelect);
    });
    document.getElementById('uploadStartBtn')?.addEventListener('click', startUploadPipeline);
    document.getElementById('confirmAllBtn')?.addEventListener('click', confirmAllPapers);
    document.getElementById('skipIncompleteBtn')?.addEventListener('click', skipIncomplete);

    document.getElementById('uploadFileList')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        if (target.dataset.action === 'remove-file') {
            removeFile(parseInt(target.dataset.fileIdx));
        }
    });

    document.querySelectorAll('[data-action="close-delete"]').forEach(btn => {
        btn.addEventListener('click', closeDeleteModal);
    });
    document.getElementById('confirmDeleteBtn')?.addEventListener('click', confirmDelete);
}

// --- Initialize ---
export async function init() {
    await loadPapersData();
    refreshStats();
    searchAndRender();
    setupEvents();
    setupPanelResize();
}
