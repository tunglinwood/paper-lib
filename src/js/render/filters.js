import { state } from '../state.js';
import { escapeHtml } from '../utils/helpers.js';
import { t } from '../i18n.js';

export function extractTopics(papers) {
    const topics = {};
    papers.forEach(paper => {
        (paper.tags || []).forEach(tag => {
            topics[tag] = (topics[tag] || 0) + 1;
        });
        const title = (paper.title || '').toLowerCase();
        if (title.includes('dorzagliatin')) topics['Dorzagliatin'] = (topics['Dorzagliatin'] || 0) + 1;
        if (title.includes('glucokinase') || title.includes('gk')) topics['Glucokinase'] = (topics['Glucokinase'] || 0) + 1;
        if (title.includes('diabetes') || title.includes('t2d')) topics['Diabetes'] = (topics['Diabetes'] || 0) + 1;
        if (title.includes('clinical')) topics['Clinical Trial'] = (topics['Clinical Trial'] || 0) + 1;
    });
    return Object.fromEntries(Object.entries(topics).sort((a, b) => b[1] - a[1]));
}

export function populateYearPills(elementId, years) {
    const div = document.getElementById(elementId);
    const unknownCount = state.allPapers.filter(p => !p.year).length;
    div.innerHTML = `
        <div class="year-pills" id="yearPillsContainer">
            ${years.map(y => `<span class="year-pill ${state.selectedYears.has(String(y)) ? 'active' : ''}" role="button" aria-label="Filter by year ${y}" data-year="${y}" data-action="toggle-year" data-year-val="${y}">${y}</span>`).join('')}
            ${unknownCount > 0 ? `<span class="year-pill ${state.selectedYears.has('unknown') ? 'active' : ''}" role="button" aria-label="Filter by unknown year" data-year="unknown" data-action="toggle-year" data-year-val="unknown">${t('unknownYear', { count: unknownCount })}</span>` : ''}
        </div>
    `;
}

export function updateYearPillUI() {
    const container = document.getElementById('yearPillsContainer');
    if (!container) return;
    container.querySelectorAll('.year-pill[data-year]').forEach(pill => {
        pill.classList.toggle('active', state.selectedYears.has(pill.dataset.year));
    });
}

export function populateTopics(topics) {
    const topicDiv = document.getElementById('topicFilters');
    topicDiv.innerHTML = Object.entries(topics).slice(0, 15).map(([topic, count]) =>
        `<span class="topic-tag" role="button" aria-label="Search topic: ${topic}" data-action="search-topic" data-topic="${escapeHtml(topic)}">${topic} (${count})</span>`
    ).join('');
}
