import { state } from '../state.js';
import { escapeHtml } from '../utils/helpers.js';
import { t } from '../i18n.js';

export function renderTrending(rankings, allPapers) {
    const list = document.getElementById('trendingList');
    if (!rankings || rankings.length === 0) {
        list.innerHTML = '<li class="trending-empty">' + t('trendingEmpty') + '</li>';
        return;
    }
    list.innerHTML = rankings.map((item, idx) => {
        const paper = allPapers.find(p => p.paper_id === item.paper_id);
        if (!paper) return '';
        const rankClass = idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : '';
        const hasHtml = !!paper.html_path;
        const action = hasHtml ? 'view-html' : 'show-paper';
        const href = hasHtml ? `/papers/${paper.paper_id}.html` : `#${paper.paper_id}`;
        const target = hasHtml ? ' target="_blank" rel="noopener"' : '';
        return `<li class="trending-item" data-action="${action}" data-id="${paper.paper_id}">
            <a href="${href}"${target} style="display:flex;align-items:gap:0.5rem;text-decoration:none;color:inherit;width:100%;">
                <span class="trending-rank ${rankClass}">${idx + 1}</span>
                <span class="trending-title">${escapeHtml(paper.title || 'Untitled')}</span>
                <span class="trending-count">${item.count}</span>
            </a>
        </li>`;
    }).join('');
}

export function updateTrendingTabs(windowDays) {
    document.querySelectorAll('.trending-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.window === windowDays);
    });
}
