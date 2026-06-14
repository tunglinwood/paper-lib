// i18n: English/Chinese translations for the Paper Library UI
// Usage: import { t, setLang, getCurrentLang } from './i18n.js';

const translations = {
    en: {
        // Header
        appTitle: 'Paper Library',
        appSubtitle: 'Research Archive - Search, Browse & Export',

        // Search
        searchPlaceholder: 'Search by title, author, venue, or keywords...',
        searchBtn: 'Search',

        // Sidebar
        yearFilter: 'Year',
        topicsFilter: 'Topics',

        // Papers list
        papersCountFmt: '{count} papers found (page {current}/{total})',
        noPapers: 'No papers found. Try adjusting your search.',
        loading: 'Loading...',
        searching: 'Searching with AI...',
        loadingPapers: 'Loading papers...',

        // Sort
        sortByRelevance: 'Sort by Relevance',
        sortByYear: 'Sort by Year',
        sortByTitle: 'Sort by Title',

        // Trending
        trending: 'Trending',
        trending7d: '7d',
        trending30d: '30d',
        trendingAll: 'All',
        trendingEmpty: 'No views yet. Start browsing!',
        trendingUnavailable: 'Trending unavailable',

        // Paper card
        untitled: 'Untitled',
        unknownAuthors: 'Unknown authors',
        relevance: 'Relevance',
        viewHtml: 'View HTML',

        // Pagination
        prev: 'Prev',
        next: 'Next',
        pageOf: 'Page {current} of {total}',

        // Modal
        year: 'Year',
        venue: 'Venue',
        doi: 'DOI',
        abstract: 'Abstract',
        relatedPapers: 'Related Papers',
        noRelatedPapers: 'No related papers found.',

        // Language toggle
        langToggle: '中文',

        // Unknown year
        unknownYear: '? ({count})',

        // Loading state
        errorLoading: 'Error loading papers:',
    },
    zh: {
        // Header
        appTitle: '论文库',
        appSubtitle: '研究文献档案 — 搜索、浏览与导出',

        // Search
        searchPlaceholder: '按标题、作者、期刊或关键词搜索...',
        searchBtn: '搜索',

        // Sidebar
        yearFilter: '年份',
        topicsFilter: '主题',

        // Papers list
        papersCountFmt: '找到 {count} 篇论文（第 {current}/{total} 页）',
        noPapers: '未找到论文，请调整搜索条件。',
        loading: '加载中...',
        searching: 'AI 智能搜索...',
        loadingPapers: '正在加载论文...',

        // Sort
        sortByRelevance: '按相关度排序',
        sortByYear: '按年份排序',
        sortByTitle: '按标题排序',

        // Trending
        trending: '热门',
        trending7d: '7天',
        trending30d: '30天',
        trendingAll: '全部',
        trendingEmpty: '暂无浏览记录，快去看看吧！',
        trendingUnavailable: '热门数据暂时不可用',

        // Paper card
        untitled: '无标题',
        unknownAuthors: '未知作者',
        relevance: '相关度',
        viewHtml: '查看 HTML',

        // Pagination
        prev: '上一页',
        next: '下一页',
        pageOf: '第 {current} 页，共 {total} 页',

        // Modal
        year: '年份',
        venue: '期刊',
        doi: 'DOI',
        abstract: '摘要',
        relatedPapers: '相关论文',
        noRelatedPapers: '未找到相关论文。',

        // Language toggle
        langToggle: 'English',

        // Unknown year
        unknownYear: '? ({count})',

        // Loading state
        errorLoading: '加载论文时出错：',
    },
};

let currentLang = 'zh';

export function t(key, params = {}) {
    const en = translations.en[key] || key;
    const zh = translations.zh[key] || key;
    let text = currentLang === 'zh' ? zh : en;
    // Replace {key} placeholders
    for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}

export function setLang(lang) {
    currentLang = lang;
    try { localStorage.setItem('paperLibLang', lang); } catch {}
    document.documentElement.lang = lang;
    applyTranslations();
}

export function getCurrentLang() {
    return currentLang;
}

// Load saved preference
try {
    const saved = localStorage.getItem('paperLibLang');
    if (saved && (saved === 'en' || saved === 'zh')) currentLang = saved;
} catch {}

// Re-render UI with current language
export function applyTranslations() {
    // Header
    const h1 = document.querySelector('.header h1');
    if (h1) h1.textContent = t('appTitle');
    const subtitle = document.querySelector('.header p');
    if (subtitle) subtitle.textContent = t('appSubtitle');

    // Search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.placeholder = t('searchPlaceholder');
    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) searchBtn.textContent = t('searchBtn');

    // Sidebar
    updateSidebarLabels();

    // Sort select
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        for (const opt of sortSelect.options) {
            if (opt.value === 'relevance') opt.text = t('sortByRelevance');
            else if (opt.value === 'year') opt.text = t('sortByYear');
            else if (opt.value === 'title') opt.text = t('sortByTitle');
        }
    }

    // Trending
    const trendingH3 = document.querySelector('.trending-header h3');
    if (trendingH3) trendingH3.textContent = t('trending');
    const trendingTabs = document.querySelectorAll('.trending-tab');
    if (trendingTabs.length) {
        trendingTabs[0].textContent = t('trending7d');
        trendingTabs[1].textContent = t('trending30d');
        trendingTabs[2].textContent = t('trendingAll');
    }

    // Modal
    const relatedH3 = document.querySelector('#relatedPapers h3');
    if (relatedH3) relatedH3.textContent = t('relatedPapers');

    // Language toggle button
    const langBtn = document.getElementById('langToggleBtn');
    if (langBtn) langBtn.textContent = t('langToggle');
}

function updateSidebarLabels() {
    const filterGroups = document.querySelectorAll('.filter-group');
    if (filterGroups.length >= 2) {
        const h3s = filterGroups[0].querySelector('h3');
        const h3s2 = filterGroups[1].querySelector('h3');
        if (h3s) h3s.textContent = t('yearFilter');
        if (h3s2) h3s2.textContent = t('topicsFilter');
    }
}
