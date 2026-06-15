import { state } from './state.js';
import { fetchIndex, searchPapers } from './api.js';
import { escapeHtml, formatSize } from './utils/helpers.js';
import { renderPapers, goPage } from './render/papers.js';
import { extractTopics, populateYearPills, updateYearPillUI, populateTopics } from './render/filters.js';
import { loadTrending, trackAndRefresh } from './actions/views.js';
import { showModal, closeModal, setupPanelResize } from './render/modal.js';
import { t, setLang, getCurrentLang, applyTranslations } from './i18n.js';
import { initAgent } from './agent.js';

// --- Data loading & initialization ---
async function loadStats() {
    const papers = await fetchIndex();
    state.allPapers = papers;

    document.getElementById('totalPapers').textContent = papers.length;
    document.getElementById('totalSize').textContent = formatSize(
        papers.reduce((sum, p) => sum + (p.file_size_bytes || 0), 0)
    );

    const years = [...new Set(papers.map(p => p.year).filter(Boolean))].sort((a, b) => b - a);
    populateYearPills('yearFilters', years);

    const topics = extractTopics(papers);
    populateTopics(topics);
}

async function loadPapers(query = '') {
    const container = document.getElementById('papersList');
    container.innerHTML =
        '<div class="loading"><div class="spinner"></div>' + t('loadingPapers') + '</div>';

    if (!query.trim()) {
        state.filteredPapers = [...state.allPapers];
        state.currentPage = 1;
        sortPapers();
        return;
    }

    try {
        const resp = await searchPapers({ q: query });
        state.filteredPapers = resp.results;
        state.currentPage = 1;
        sortPapers();
    } catch (err) {
        console.error('Search failed:', err);
        container.innerHTML = `<div class="loading">${t('errorLoading')} ${err.message}</div>`;
    }
}

async function searchPapersFn() {
    const query = document.getElementById('searchInput').value;

    if (!query.trim()) {
        state.filteredPapers = [...state.allPapers];
        state.currentPage = 1;
        sortPapers();
        return;
    }

    const container = document.getElementById('papersList');
    container.innerHTML =
        '<div class="loading"><div class="spinner"></div>' + t('searching') + '</div>';

    try {
        const resp = await searchPapers({ q: query });
        state.filteredPapers = resp.results;
        state.currentPage = 1;
        // Relevance order from API; don't re-sort
        renderPapers();
    } catch (err) {
        console.error('Search failed:', err);
        container.innerHTML = `<div class="loading">${t('errorLoading')} ${err.message}</div>`;
    }
}

// --- Filter & sort ---
function applyFilters() {
    const query = document.getElementById('searchInput').value;

    if (state.selectedYears.size === 0) {
        loadPapers(query);
        return;
    }

    const selectedYears = state.selectedYears;
    let results = state.filteredPapers.filter(p => {
        const key = p.year ? String(p.year) : 'unknown';
        return selectedYears.has(key);
    });

    state.filteredPapers = results;
    state.currentPage = 1;
    renderPapers();
}

function sortPapers() {
    const sort = document.getElementById('sortSelect').value;
    if (sort === 'year') {
        state.filteredPapers.sort((a, b) => (b.year || 0) - (a.year || 0));
    } else if (sort === 'title') {
        state.filteredPapers.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    renderPapers();
}

function toggleYear(year) {
    if (state.selectedYears.has(year)) state.selectedYears.delete(year);
    else state.selectedYears.add(year);
    updateYearPillUI();
    applyFilters();
}

// --- Event delegation ---
function setupEventDelegation() {
    // Main content area
    document.getElementById('papersList')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        const action = target.dataset.action;
        const id = target.dataset.id;

        switch (action) {
            case 'show-paper': e.preventDefault(); showPaper(id); break;
            case 'view-html':
                // For papers with HTML, the link has target="_blank" so browser handles it
                // But we prevent default just in case and let the href work
                e.preventDefault();
                window.open(target.href, '_blank', 'noopener');
                break;
        }
    });

    // Pagination (injected after papersList, inside <main>)
    document.querySelector('main')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action="go-page"]');
        if (target) {
            e.preventDefault();
            goPage(parseInt(target.dataset.page, 10));
        }
    });

    // Sidebar
    document.getElementById('yearFilters')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action="toggle-year"]');
        if (target) toggleYear(target.dataset.yearVal);
    });

    document.getElementById('topicFilters')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action="search-topic"]');
        if (target) searchByTopic(target.dataset.topic);
    });

    // Related papers (inside modal)
    document.getElementById('paperModal')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action="show-paper"]');
        if (target) { e.preventDefault(); showPaper(target.dataset.id); return; }

        // Also handle modal close
        if (e.target.id === 'paperModal' || e.target.classList.contains('modal-close')) closeModal();
    });

    // Trending items
    document.getElementById('trendingList')?.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action="show-paper"]');
        if (target) { e.preventDefault(); showPaper(target.dataset.id); }
    });

    // Trending tabs
    document.querySelectorAll('.trending-tab').forEach(tab => {
        tab.addEventListener('click', () => loadTrending(tab.dataset.window));
    });

    // Search button
    document.querySelector('.search-btn')?.addEventListener('click', searchPapersFn);

    // Search enter key
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchPapersFn();
    });

    // Debounced auto-search on input (covers page agent programmatic typing)
    let searchDebounce = null;
    document.getElementById('searchInput')?.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => searchPapersFn(), 500);
    });

    // Sort select
    document.getElementById('sortSelect')?.addEventListener('change', sortPapers);
}

// --- Actions that need data context ---
function showPaper(paperId) {
    const paper = state.allPapers.find(p => p.paper_id === paperId);
    if (!paper) return;
    showModal(paper);
}

// --- Hash routing ---
function handleHash() {
    const hash = window.location.hash.slice(1);
    if (hash && state.allPapers.find(p => p.paper_id === hash)) {
        showPaper(hash);
    }
}

function searchByTopic(topic) {
    document.getElementById('searchInput').value = topic;
    loadPapers(topic);
}

// --- Initialize ---
export async function init() {
    try {
        await loadStats();
        applyTranslations();
    } catch (err) {
        console.error('Failed to load paper index:', err);
        document.getElementById('papersList').innerHTML =
            `<div class="loading">${t('errorLoading')} ${err.message}</div>`;
    }
    await loadPapers();
    await loadTrending('7');
    setupEventDelegation();
    setupPanelResize();
    setupLangToggle();
    window.addEventListener('hashchange', handleHash);
    handleHash();
    await initAgent();
}

function setupLangToggle() {
    const btn = document.getElementById('langToggleBtn');
    if (!btn) return;
    btn.textContent = t('langToggle');
    btn.addEventListener('click', () => {
        const newLang = getCurrentLang() === 'en' ? 'zh' : 'en';
        setLang(newLang);
    });
}
