import { state } from '../state.js';
import { escapeHtml } from '../utils/helpers.js';
import { t } from '../i18n.js';

export function renderPapers() {
    const container = document.getElementById('papersList');
    const totalPages = Math.max(1, Math.ceil(state.filteredPapers.length / state.PAGE_SIZE));
    if (state.currentPage > totalPages) state.currentPage = totalPages;
    const start = (state.currentPage - 1) * state.PAGE_SIZE;
    const pagePapers = state.filteredPapers.slice(start, start + state.PAGE_SIZE);

    document.getElementById('papersCount').textContent =
        t('papersCountFmt', { count: state.filteredPapers.length, current: state.currentPage, total: totalPages });

    if (pagePapers.length === 0) {
        container.innerHTML = '<div class="loading">' + t('noPapers') + '</div>';
        renderPaginationControls(0);
        return;
    }

    container.innerHTML = pagePapers.map(paper => {
        const similarity = paper._similarity != null ? paper._similarity : null;
        return `
        <div class="paper-card" data-id="${paper.paper_id}">
            <h3 class="paper-title"><a href="#${paper.paper_id}" data-action="show-paper" data-id="${paper.paper_id}">${escapeHtml(paper.title || 'Untitled')}</a></h3>
            <p class="paper-authors">${escapeHtml((paper.authors || []).join(', ') || t('unknownAuthors'))}</p>
            <div class="paper-meta">
                ${paper.year ? `<span>📅 ${paper.year}</span>` : ''}
                ${paper.venue ? `<span>📖 ${escapeHtml(paper.venue)}</span>` : ''}
                ${paper.doi ? `<span class="tag doi">DOI: ${paper.doi}</span>` : ''}
                ${similarity != null ? `<span class="tag" style="background:#e0f2fe;color:#0369a1;">${t('relevance')}: ${(similarity * 100).toFixed(0)}%</span>` : ''}
            </div>
            <div class="paper-tags">
                ${(paper.tags || []).slice(0, 5).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
            </div>
            ${paper.html_path ? `<div class="paper-actions">
    <a href="/papers/${paper.paper_id}.html" target="_blank" rel="noopener" data-action="view-html" class="action-btn html-btn">${t('viewHtml')}</a>
</div>` : ''}
        </div>
    `}).join('');

    renderPaginationControls(totalPages);
}

function renderPaginationControls(totalPages) {
    const existing = document.getElementById('paginationControls');
    if (existing) existing.remove();
    if (totalPages <= 1) return;

    const wrapper = document.createElement('div');
    wrapper.id = 'paginationControls';
    wrapper.className = 'pagination';

    let html = `<button class="page-btn" aria-label="Previous page" ${state.currentPage === 1 ? 'disabled' : ''} data-action="go-page" data-page="${state.currentPage - 1}">&laquo; ${t('prev')}</button>`;

    const pages = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        pages.push(1);
        if (state.currentPage > 3) pages.push('...');
        const s = Math.max(2, state.currentPage - 1), e = Math.min(totalPages - 1, state.currentPage + 1);
        if (s > 2 && !pages.includes('...')) pages.push('...');
        for (let i = s; i <= e; i++) pages.push(i);
        if (e < totalPages - 1) pages.push('...');
        pages.push(totalPages);
    }

    for (const p of pages) {
        if (p === '...') {
            html += `<span class="page-info">…</span>`;
        } else {
            html += `<button class="page-btn ${p === state.currentPage ? 'active' : ''}" aria-label="Go to page ${p}" data-action="go-page" data-page="${p}">${p}</button>`;
        }
    }

    html += `<button class="page-btn" aria-label="Next page" ${state.currentPage === totalPages ? 'disabled' : ''} data-action="go-page" data-page="${state.currentPage + 1}">${t('next')} &raquo;</button>`;
    html += `<span class="page-info">${t('pageOf', { current: state.currentPage, total: totalPages })}</span>`;

    wrapper.innerHTML = html;
    document.getElementById('papersList').after(wrapper);
}

export function goPage(page) {
    const totalPages = Math.ceil(state.filteredPapers.length / state.PAGE_SIZE);
    if (page < 1 || page > totalPages) return;
    state.currentPage = page;
    renderPapers();
    document.getElementById('papersList').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
