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
        return `<li class="trending-item" data-action="show-paper" data-id="${paper.paper_id}">
            <span class="trending-rank ${rankClass}">${idx + 1}</span>
            <span class="trending-title">${escapeHtml(paper.title || 'Untitled')}</span>
            <span class="trending-count">${item.count}</span>
        </li>`;
    }).join('');
}

export function updateTrendingTabs(windowDays) {
    document.querySelectorAll('.trending-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.window === windowDays);
    });
}
